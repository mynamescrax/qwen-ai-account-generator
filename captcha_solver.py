import time
import random
import math
import logging
import base64
import io
from typing import Optional, Dict, Tuple, List, Any
from dataclasses import dataclass, field
from playwright.sync_api import Page

try:
    import requests
except ImportError:
    requests = None

try:
    import cv2
    import numpy as np
    _HAS_CV2 = True
except ImportError:
    _HAS_CV2 = False
    np = None

try:
    from PIL import Image
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False


@dataclass
class MovementPoint:
    x: float
    y: float
    timestamp: float


@dataclass
class DistanceResult:
    method: str
    distance: float
    hole_x1: float = 0.0
    hole_x2: float = 0.0
    confidence: float = 1.0


@dataclass
class VoteResult:
    distance: float
    confidence: float
    methods: Dict[str, float] = field(default_factory=dict)
    spread: float = 0.0


class HumanBehaviorSimulator:

    def __init__(self, page: Page):
        self.page = page
        self._last_position = None
        self._viewport = page.viewport_size or {'width': 1280, 'height': 720}
        self._stored_x: Optional[float] = None
        self._stored_y: Optional[float] = None

    def _get_current_position(self) -> Tuple[float, float]:
        if self._stored_x is not None and self._stored_y is not None:
            return (self._stored_x, self._stored_y)
        return (self._viewport['width'] // 2, self._viewport['height'] // 2)

    def _track_move(self, x: float, y: float):
        self._stored_x = x
        self._stored_y = y

    def _generate_bezier_curve(self, start: Tuple[float, float],
                               end: Tuple[float, float],
                               num_points: int = None) -> List[Tuple[float, float]]:
        if num_points is None:
            num_points = random.randint(25, 45)

        cx1 = start[0] + (end[0] - start[0]) * random.uniform(0.2, 0.4) + random.uniform(-30, 30)
        cy1 = start[1] + (end[1] - start[1]) * random.uniform(0.2, 0.4) + random.uniform(-20, 20)
        cx2 = start[0] + (end[0] - start[0]) * random.uniform(0.6, 0.8) + random.uniform(-30, 30)
        cy2 = start[1] + (end[1] - start[1]) * random.uniform(0.6, 0.8) + random.uniform(-20, 20)

        points = []
        for i in range(num_points + 1):
            t = i / num_points
            eased_t = t * t * (3 - 2 * t)
            x = ((1 - eased_t) ** 3 * start[0]
                 + 3 * (1 - eased_t) ** 2 * eased_t * cx1
                 + 3 * (1 - eased_t) * eased_t ** 2 * cx2
                 + eased_t ** 3 * end[0])
            y = ((1 - eased_t) ** 3 * start[1]
                 + 3 * (1 - eased_t) ** 2 * eased_t * cy1
                 + 3 * (1 - eased_t) * eased_t ** 2 * cy2
                 + eased_t ** 3 * end[1])
            x += random.uniform(-0.5, 0.5)
            y += random.uniform(-0.5, 0.5)
            points.append((x, y))
        return points

    def _get_random_start_position(self) -> Tuple[float, float]:
        x = random.randint(self._viewport['width'] // 4, self._viewport['width'] * 3 // 4)
        y = random.randint(self._viewport['height'] // 2, self._viewport['height'] * 9 // 10)
        if self._stored_x is not None and self._stored_y is not None:
            x = self._stored_x + random.randint(-50, 50)
            y = self._stored_y + random.randint(-50, 50)
            x = max(0, min(self._viewport['width'], x))
            y = max(0, min(self._viewport['height'], y))
        return x, y

    def move_to(self, target_x: float, target_y: float,
                human: bool = True, hesitate: bool = False) -> None:
        start_x, start_y = self._get_current_position()

        if start_x == 0 and start_y == 0:
            start_x, start_y = self._get_random_start_position()
            self.page.mouse.move(start_x, start_y)
            self._track_move(start_x, start_y)
            time.sleep(random.uniform(0.1, 0.5))

        if not human:
            self.page.mouse.move(target_x, target_y)
            self._track_move(target_x, target_y)
            return

        points = self._generate_bezier_curve((start_x, start_y), (target_x, target_y))
        base_duration = random.uniform(0.3, 0.8)
        step_duration = base_duration / len(points)

        for i, (x, y) in enumerate(points):
            t = i / len(points)
            if t < 0.15:
                delay = step_duration * random.uniform(1.5, 2.5)
            elif t < 0.85:
                delay = step_duration * random.uniform(0.5, 0.8)
            else:
                delay = step_duration * random.uniform(1.2, 2.0)

            if random.random() < 0.01 and 0.2 < t < 0.8:
                time.sleep(random.uniform(0.02, 0.08))

            self.page.mouse.move(x, y)
            self._track_move(x, y)
            time.sleep(delay)

        for _ in range(random.randint(2, 5)):
            adj_x = target_x + random.uniform(-1.5, 1.5)
            adj_y = target_y + random.uniform(-1.5, 1.5)
            self.page.mouse.move(adj_x, adj_y)
            self._track_move(adj_x, adj_y)
            time.sleep(random.uniform(0.01, 0.03))

        self.page.mouse.move(target_x, target_y)
        self._track_move(target_x, target_y)

        if hesitate:
            time.sleep(random.uniform(0.1, 0.4))

    def click_with_offset(self, element_box: Dict,
                          offset_type: str = 'normal') -> Tuple[float, float]:
        if not element_box:
            return 0, 0

        center_x = element_box.get('x', 0) + element_box.get('width', 0) / 2
        center_y = element_box.get('y', 0) + element_box.get('height', 0) / 2
        width = element_box.get('width', 40)
        height = element_box.get('height', 40)

        if offset_type == 'normal':
            offset_x = random.gauss(0, width * 0.15)
            offset_y = random.gauss(0, height * 0.15)
        elif offset_type == 'edge':
            if random.random() < 0.5:
                offset_x = -width * random.uniform(0.3, 0.4)
            else:
                offset_x = width * random.uniform(0.3, 0.4)
            offset_y = random.gauss(0, height * 0.2)
        else:
            offset_x = random.uniform(-width * 0.3, width * 0.3)
            offset_y = random.uniform(-height * 0.3, height * 0.3)

        click_x = center_x + offset_x
        click_y = center_y + offset_y

        click_x = max(element_box.get('x', 0) + 2,
                      min(element_box.get('x', 0) + width - 2, click_x))
        click_y = max(element_box.get('y', 0) + 2,
                      min(element_box.get('y', 0) + height - 2, click_y))

        self.move_to(click_x, click_y, human=True, hesitate=True)
        return click_x, click_y


class DistanceCalculator:

    DEFAULT_CONFIDENCE = {
        'ddddocr_cropped': 0.90,
        'ddddocr_full':    0.85,
        'cv2_edge':        0.85,
        'cv2_gray':        0.80,
        'variance':        0.50,
    }

    def __init__(self, ocr, logger, config: Optional[Dict] = None):
        self.ocr = ocr
        self.logger = logger
        self.config = config or {}
        self.min_hole_x = self.config.get('min_hole_x_native', 20)
        self.cv2_threshold = self.config.get('template_match_threshold', 0.30)
        self.voting_tolerance = self.config.get('distance_voting_tolerance', 5.0)

    def calculate(self, captcha_data: Dict) -> Optional[VoteResult]:
        if not _HAS_PIL or not _HAS_CV2:
            self.logger.warning("PIL/cv2 unavailable — falling back to ddddocr-only")
            return self._fallback_ddddocr_only(captcha_data)

        results: List[DistanceResult] = []

        r = self._method_ddddocr_cropped(captcha_data)
        if r:
            results.append(r)

        r = self._method_ddddocr_full(captcha_data)
        if r:
            results.append(r)

        r = self._method_cv2_edge(captcha_data)
        if r:
            results.append(r)

        r = self._method_cv2_gray(captcha_data)
        if r:
            results.append(r)

        r = self._method_variance(captcha_data)
        if r:
            results.append(r)

        if not results:
            return None

        return self._vote(results)

    def _extract_piece_bbox(self, puzzle_img) -> Optional[Tuple[int, int, int, int]]:
        arr = np.array(puzzle_img)
        if arr.ndim != 3:
            return None

        if arr.shape[2] >= 4:
            alpha = arr[:, :, 3]
            mask = alpha > 30
        else:
            gray = arr[:, :, 0]
            mask = gray < 240

        cols = np.any(mask, axis=0)
        rows = np.any(mask, axis=1)
        if not cols.any() or not rows.any():
            return None

        x1 = int(np.argmax(cols))
        y1 = int(np.argmax(rows))
        x2 = int(len(cols) - np.argmax(cols[::-1]))
        y2 = int(len(rows) - np.argmax(rows[::-1]))

        if x2 - x1 < 5 or y2 - y1 < 5:
            return None

        return (x1, y1, x2, y2)

    def _to_drag_distance(self, hole_x1_native: float, hole_x2_native: float,
                          piece_x1_native: float, piece_x2_native: float,
                          data: Dict) -> float:
        bg_natural = data.get('bg_natural_width') or 1
        bg_css = data.get('bg_css_width') or bg_natural
        scale = bg_css / bg_natural if bg_natural else 1.0

        puzzle_natural = data.get('puzzle_natural_width') or 1
        puzzle_css = data.get('puzzle_css_width') or puzzle_natural
        puzzle_scale = puzzle_css / puzzle_natural if puzzle_natural else scale

        puzzle_left_css = data.get('puzzle_left_css', 0.0)

        hole_center_native = (hole_x1_native + hole_x2_native) / 2.0
        hole_center_screen = hole_center_native * scale

        piece_center_native = (piece_x1_native + piece_x2_native) / 2.0
        piece_center_screen = puzzle_left_css + (piece_center_native * puzzle_scale)

        return hole_center_screen - piece_center_screen

    def _method_ddddocr_cropped(self, data: Dict) -> Optional[DistanceResult]:
        try:
            puzzle_img = Image.open(io.BytesIO(data['shadow_bytes'])).convert('RGBA')
            bbox = self._extract_piece_bbox(puzzle_img)
            if not bbox:
                return None
            x1, y1, x2, y2 = bbox

            cropped = puzzle_img.crop((x1, y1, x2, y2))

            pad = 10
            padded = Image.new('RGBA',
                               (cropped.width + pad * 2, cropped.height + pad * 2),
                               (0, 0, 0, 0))
            padded.paste(cropped, (pad, pad))
            buf = io.BytesIO()
            padded.save(buf, format='PNG')
            cropped_bytes = buf.getvalue()

            result = None
            for simple in (False, True):
                try:
                    r = self.ocr.slide_match(cropped_bytes, data['bg_bytes'],
                                             simple_target=simple)
                    if r and 'target' in r:
                        result = r
                        break
                except Exception:
                    continue

            if not result or 'target' not in result:
                return None

            target = result['target']
            if len(target) < 4:
                return None

            hole_x1, _, hole_x2, _ = target
            if hole_x1 < self.min_hole_x:
                self.logger.debug(f"ddddocr_cropped: rejected origin match x1={hole_x1}")
                return None

            distance = self._to_drag_distance(hole_x1, hole_x2, x1, x2, data)
            return DistanceResult(
                method='ddddocr_cropped',
                distance=distance,
                hole_x1=float(hole_x1),
                hole_x2=float(hole_x2),
                confidence=self.DEFAULT_CONFIDENCE['ddddocr_cropped'],
            )
        except Exception as e:
            self.logger.debug(f"ddddocr_cropped failed: {e}")
            return None

    def _method_ddddocr_full(self, data: Dict) -> Optional[DistanceResult]:
        try:
            puzzle_img = Image.open(io.BytesIO(data['shadow_bytes'])).convert('RGBA')
            bbox = self._extract_piece_bbox(puzzle_img)
            if not bbox:
                return None
            x1, y1, x2, y2 = bbox

            result = self.ocr.slide_match(data['shadow_bytes'], data['bg_bytes'],
                                          simple_target=False)
            if not result or 'target' not in result:
                return None

            target = result['target']
            if len(target) < 4:
                return None

            hole_x1, _, hole_x2, _ = target
            if hole_x1 < self.min_hole_x:
                return None

            distance = self._to_drag_distance(hole_x1, hole_x2, x1, x2, data)
            return DistanceResult(
                method='ddddocr_full',
                distance=distance,
                hole_x1=float(hole_x1),
                hole_x2=float(hole_x2),
                confidence=self.DEFAULT_CONFIDENCE['ddddocr_full'],
            )
        except Exception as e:
            self.logger.debug(f"ddddocr_full failed: {e}")
            return None

    def _method_cv2_edge(self, data: Dict) -> Optional[DistanceResult]:
        if not _HAS_CV2:
            return None
        try:
            puzzle_img = Image.open(io.BytesIO(data['shadow_bytes'])).convert('RGBA')
            arr = np.array(puzzle_img)
            if arr.ndim != 3 or arr.shape[2] < 4:
                return None
            alpha = arr[:, :, 3]

            bbox = self._extract_piece_bbox(puzzle_img)
            if not bbox:
                return None
            x1, y1, x2, y2 = bbox

            piece_edges = cv2.Canny(alpha, 50, 150)

            bg_arr = np.array(Image.open(io.BytesIO(data['bg_bytes'])).convert('RGB'))
            bg_gray = cv2.cvtColor(bg_arr, cv2.COLOR_RGB2GRAY)
            bg_edges = cv2.Canny(bg_gray, 50, 150)

            if piece_edges.max() == 0 or bg_edges.max() == 0:
                return None

            (ph, pw) = piece_edges.shape[:2]
            (bh, bw) = bg_edges.shape[:2]
            if ph > bh or pw > bw:
                return None

            res = cv2.matchTemplate(bg_edges, piece_edges, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)

            if max_val < self.cv2_threshold:
                self.logger.debug(f"cv2_edge: low confidence {max_val:.3f}")
                return None

            piece_w = x2 - x1
            hole_x1 = float(max_loc[0] + x1)
            hole_x2 = hole_x1 + piece_w

            if hole_x1 < self.min_hole_x:
                return None

            distance = self._to_drag_distance(hole_x1, hole_x2, x1, x2, data)
            return DistanceResult(
                method='cv2_edge',
                distance=distance,
                hole_x1=hole_x1,
                hole_x2=hole_x2,
                confidence=max(0.4, min(1.0, (max_val - 0.2) / 0.5)),
            )
        except Exception as e:
            self.logger.debug(f"cv2_edge failed: {e}")
            return None

    def _method_cv2_gray(self, data: Dict) -> Optional[DistanceResult]:
        if not self.config.get('enable_cv2_gray', False):
            return None
        if not _HAS_CV2:
            return None
        try:
            puzzle_img = Image.open(io.BytesIO(data['shadow_bytes'])).convert('RGBA')
            arr = np.array(puzzle_img)
            if arr.ndim != 3 or arr.shape[2] < 4:
                return None
            alpha = arr[:, :, 3].astype(np.uint8)

            bbox = self._extract_piece_bbox(puzzle_img)
            if not bbox:
                return None
            x1, y1, x2, y2 = bbox

            bg_arr = np.array(Image.open(io.BytesIO(data['bg_bytes'])).convert('RGB'))
            bg_gray = cv2.cvtColor(bg_arr, cv2.COLOR_RGB2GRAY)
            bg_gray = cv2.GaussianBlur(bg_gray, (3, 3), 0)
            bg_inv = cv2.bitwise_not(bg_gray)

            (ph, pw) = alpha.shape[:2]
            (bh, bw) = bg_inv.shape[:2]
            if ph > bh or pw > bw:
                return None

            res = cv2.matchTemplate(bg_inv, alpha, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)

            if max_val < self.cv2_threshold:
                self.logger.debug(f"cv2_gray: low confidence {max_val:.3f}")
                return None

            piece_w = x2 - x1
            hole_x1 = float(max_loc[0] + x1)
            hole_x2 = hole_x1 + piece_w

            if hole_x1 < self.min_hole_x:
                return None

            distance = self._to_drag_distance(hole_x1, hole_x2, x1, x2, data)
            return DistanceResult(
                method='cv2_gray',
                distance=distance,
                hole_x1=hole_x1,
                hole_x2=hole_x2,
                confidence=max(0.3, min(0.95, (max_val - 0.2) / 0.5)),
            )
        except Exception as e:
            self.logger.debug(f"cv2_gray failed: {e}")
            return None

    def _method_variance(self, data: Dict) -> Optional[DistanceResult]:
        if not self.config.get('enable_variance_method', False):
            return None
        if not _HAS_CV2:
            return None
        try:
            bg_arr = np.array(Image.open(io.BytesIO(data['bg_bytes'])).convert('L'))
            if bg_arr.size == 0:
                return None

            col_mean = np.mean(bg_arr, axis=0).astype(np.float32)
            median_val = float(np.median(col_mean))

            dark_margin = 25.0
            dark_threshold = median_val - dark_margin
            dark_cols = col_mean < dark_threshold

            start_col = int(bg_arr.shape[1] * 0.15)
            dark_cols[:start_col] = False

            if not dark_cols.any():
                return self._variance_fallback(data, bg_arr, start_col)

            regions: List[Tuple[int, int]] = []
            in_region = False
            region_start = 0
            for i, is_dark in enumerate(dark_cols):
                if is_dark and not in_region:
                    region_start = i
                    in_region = True
                elif not is_dark and in_region:
                    regions.append((region_start, i - 1))
                    in_region = False
            if in_region:
                regions.append((region_start, len(dark_cols) - 1))

            if not regions:
                return self._variance_fallback(data, bg_arr, start_col)

            regions.sort(key=lambda r: r[1] - r[0], reverse=True)
            first_dark, last_dark = regions[0]
            hole_center_native = (first_dark + last_dark) / 2.0

            puzzle_img = Image.open(io.BytesIO(data['shadow_bytes'])).convert('RGBA')
            bbox = self._extract_piece_bbox(puzzle_img)
            if not bbox:
                return None
            x1, y1, x2, y2 = bbox
            piece_w = x2 - x1

            hole_x1 = float(hole_center_native - piece_w / 2)
            hole_x2 = float(hole_center_native + piece_w / 2)

            if hole_x1 < self.min_hole_x:
                return None

            distance = self._to_drag_distance(hole_x1, hole_x2, x1, x2, data)
            return DistanceResult(
                method='variance',
                distance=distance,
                hole_x1=hole_x1,
                hole_x2=hole_x2,
                confidence=self.DEFAULT_CONFIDENCE['variance'],
            )
        except Exception as e:
            self.logger.debug(f"variance failed: {e}")
            return None

    def _variance_fallback(self, data: Dict, bg_arr: 'np.ndarray',
                           start_col: int) -> Optional[DistanceResult]:
        try:
            col_var = np.var(bg_arr, axis=0).astype(np.float32)
            if start_col >= len(col_var):
                return None
            valid = col_var[start_col:]
            kernel = np.ones(7, dtype=np.float32) / 7.0
            smoothed = np.convolve(valid, kernel, mode='same')
            max_idx = int(np.argmax(smoothed))
            hole_center_native = start_col + max_idx

            puzzle_img = Image.open(io.BytesIO(data['shadow_bytes'])).convert('RGBA')
            bbox = self._extract_piece_bbox(puzzle_img)
            if not bbox:
                return None
            x1, y1, x2, y2 = bbox
            piece_w = x2 - x1
            hole_x1 = float(hole_center_native - piece_w / 2)
            hole_x2 = float(hole_center_native + piece_w / 2)
            if hole_x1 < self.min_hole_x:
                return None
            distance = self._to_drag_distance(hole_x1, hole_x2, x1, x2, data)
            return DistanceResult(
                method='variance',
                distance=distance,
                hole_x1=hole_x1,
                hole_x2=hole_x2,
                confidence=self.DEFAULT_CONFIDENCE['variance'] * 0.7,
            )
        except Exception:
            return None

    def _vote(self, results: List[DistanceResult]) -> VoteResult:
        sorted_results = sorted(results, key=lambda r: r.distance)

        if len(sorted_results) == 1:
            r = sorted_results[0]
            return VoteResult(
                distance=r.distance,
                confidence=r.confidence * 0.5,
                methods={r.method: r.distance},
                spread=0.0,
            )

        distances = [r.distance for r in sorted_results]
        weights = [r.confidence for r in sorted_results]

        total_w = sum(weights)
        cumulative = 0.0
        weighted_median = distances[-1]
        for d, w in zip(distances, weights):
            cumulative += w
            if cumulative >= total_w / 2.0:
                weighted_median = d
                break

        spread = max(distances) - min(distances)

        agreeing = sum(1 for d in distances
                       if abs(d - weighted_median) <= self.voting_tolerance)
        confidence = agreeing / len(distances)

        if spread > 25:
            confidence *= 0.4
        elif spread > 15:
            confidence *= 0.7
        elif spread > 8:
            confidence *= 0.9

        methods_dict = {r.method: r.distance for r in sorted_results}

        self.logger.info(
            f"    Vote: median={weighted_median:.2f}px "
            f"spread={spread:.2f} conf={confidence:.2f} "
            f"methods={ {k: round(v, 1) for k, v in methods_dict.items()} }"
        )

        return VoteResult(
            distance=weighted_median,
            confidence=confidence,
            methods=methods_dict,
            spread=spread,
        )

    def _fallback_ddddocr_only(self, data: Dict) -> Optional[VoteResult]:
        try:
            result = self.ocr.slide_match(data['shadow_bytes'], data['bg_bytes'],
                                          simple_target=False)
            if not result or 'target' not in result:
                return None
            target = result['target']
            if len(target) < 4:
                return None

            hole_x1, _, hole_x2, _ = target
            if hole_x1 < self.min_hole_x:
                return None

            puzzle_w = data.get('puzzle_natural_width') or 60
            piece_x1 = int(puzzle_w * 0.25)
            piece_x2 = int(puzzle_w * 0.75)

            distance = self._to_drag_distance(hole_x1, hole_x2,
                                              piece_x1, piece_x2, data)
            return VoteResult(
                distance=distance,
                confidence=0.4,
                methods={'ddddocr_only': distance},
                spread=0.0,
            )
        except Exception as e:
            self.logger.debug(f"Fallback failed: {e}")
            return None


class CaptchaSolver:

    def __init__(self, logger_instance=None, config=None):
        self.logger = logger_instance or logging.getLogger(__name__)
        self.config = config or {}
        self.attempts = 0
        self.consecutive_fails = 0
        self.human: Optional[HumanBehaviorSimulator] = None
        self._page: Optional[Page] = None
        self._start_time = 0
        self._ddddocr = None

        self._adaptive_offset = 0.0
        self._attempt_history: List[Tuple[float, float, bool]] = []

    def _get_ocr(self):
        if self._ddddocr is None:
            import ddddocr
            try:
                self._ddddocr = ddddocr.DdddOcr(det=False, ocr=False, show_ad=False)
            except TypeError:
                self._ddddocr = ddddocr.DdddOcr(det=False, ocr=False)
        return self._ddddocr

    def solve(self, page: Page) -> Optional[str]:
        self._page = page
        self.human = HumanBehaviorSimulator(page)
        self.attempts += 1
        self._start_time = time.time()

        self.logger.info(f"Hybrid Solve v2.14 attempt {self.attempts}")

        max_attempts = self.config.get('max_captcha_attempts', 15)
        min_confidence = self.config.get('min_confidence_threshold', 0.4)

        for attempt in range(max_attempts):
            self.logger.info(f"  [{attempt + 1}/{max_attempts}]")

            is_first = (attempt == 0)
            if not self._wait_for_slider_with_reading(page, slow_reading=is_first):
                time.sleep(0.2)
                continue

            if attempt > 0:
                time.sleep(random.uniform(0.5, 1.0))
                if not self._wait_for_slider_with_reading(page, slow_reading=False):
                    continue

            result = self._human_solve(page, min_confidence)

            if result == 'success':
                self.consecutive_fails = 0
                return self._on_success(page)
            elif result == 'failed':
                self.consecutive_fails += 1
            elif result == 'refresh':
                self._fast_refresh(page)

            time.sleep(0.2)

        self.logger.error("  Failed after all attempts")
        return None

    def _wait_for_slider_with_reading(self, page: Page, timeout: int = 5,
                                      slow_reading: bool = True) -> bool:
        if slow_reading:
            viewport = page.viewport_size
            if viewport and viewport.get('width', 0) > 100:
                x = random.randint(viewport['width'] // 3, viewport['width'] * 2 // 3)
                y = random.randint(viewport['height'] // 4, viewport['height'] // 2)
                self.human.move_to(x, y, human=True)

        try:
            selectors = ['#aliyunCaptcha-sliding-slider', '[id*="sliding-slider"]']
            for sel in selectors:
                try:
                    page.locator(sel).wait_for(state='visible', timeout=timeout * 1000)
                    time.sleep(0.1)
                    return True
                except Exception:
                    continue
            return False
        except Exception:
            return False

    def _fast_refresh(self, page: Page):
        try:
            time.sleep(0.2)
            refresh = page.locator('#aliyunCaptcha-btn-refresh')
            if refresh.count() > 0 and refresh.is_visible():
                box = refresh.bounding_box()
                if box:
                    cx = box['x'] + box['width'] / 2 + random.uniform(-3, 3)
                    cy = box['y'] + box['height'] / 2 + random.uniform(-3, 3)
                    self.human.move_to(cx, cy, human=True, hesitate=False)
                    page.mouse.click(cx, cy)
        except Exception as e:
            self.logger.debug(f"Refresh error: {e}")

    def _human_solve(self, page: Page, min_confidence: float) -> str:
        try:
            slider = page.locator('#aliyunCaptcha-sliding-slider')
            if slider.count() == 0:
                return 'failed'
            box = slider.bounding_box()
            if not box:
                return 'failed'

            self._human_scan_image(page)
            captcha_data = self._get_captcha_data(page)
            if not captcha_data:
                return 'failed'

            vote = self._calculate_distance_v2(captcha_data)
            if vote is None:
                self.logger.warning("    All distance methods failed — refreshing")
                return 'refresh'

            max_spread = self.config.get('max_acceptable_spread', 30.0)
            min_conf = self.config.get('min_acceptable_confidence', 0.40)
            if vote.spread > max_spread and vote.confidence < min_conf:
                self.logger.info(
                    f"    Methods disagree (spread={vote.spread:.1f}px, "
                    f"conf={vote.confidence:.2f}) — refreshing for a clearer image"
                )
                return 'refresh'

            base_distance = vote.distance + random.uniform(-0.5, 0.5)
            target = int(max(30, min(350, base_distance)))

            self.logger.info(
                f"    Drag target: {target}px "
                f"(vote={vote.distance:.2f}, conf={vote.confidence:.2f}, "
                f"spread={vote.spread:.2f}, methods={len(vote.methods)})"
            )

            slider_cx = box['x'] + box['width'] / 2
            slider_cy = box['y'] + box['height'] / 2

            try:
                piece_before = page.evaluate("""
                    () => {
                        const p = document.querySelector('#aliyunCaptcha-puzzle');
                        if (!p) return null;
                        return p.getBoundingClientRect().x;
                    }
                """)
            except Exception:
                piece_before = None

            drag_dead_zone = self.config.get('drag_dead_zone', 96.0)
            drag_ratio = self.config.get('drag_ratio', 1.52)
            mouse_distance = int(target / drag_ratio + drag_dead_zone)

            self.logger.info(
                f"    Drag: target={target}px "
                f"mouse={mouse_distance}px "
                f"(dead_zone={drag_dead_zone}, ratio={drag_ratio})"
            )

            page.mouse.move(slider_cx, slider_cy)
            time.sleep(random.uniform(0.15, 0.3))
            page.mouse.down()
            time.sleep(random.uniform(0.15, 0.25))

            try:
                grabbed = page.locator('#aliyunCaptcha-sliding-slider').bounding_box()
                if grabbed:
                    slider_cx = grabbed['x'] + grabbed['width'] / 2
                    slider_cy = grabbed['y'] + grabbed['height'] / 2
            except Exception:
                pass

            end_x = slider_cx + mouse_distance
            end_y = slider_cy + random.uniform(-2, 2)
            num_steps = random.randint(25, 40)
            total_time = random.uniform(0.4, 0.7)

            for i in range(num_steps + 1):
                t = i / num_steps
                eased = 1 - (1 - t) ** 3
                x = slider_cx + (end_x - slider_cx) * eased
                y = slider_cy + (end_y - slider_cy) * eased
                y += math.sin(t * math.pi) * random.uniform(-1, 1)
                page.mouse.move(x, y)
                time.sleep(total_time / num_steps * random.uniform(0.8, 1.2))

            time.sleep(random.uniform(0.1, 0.2))

            try:
                piece_after = page.evaluate("""
                    () => {
                        const p = document.querySelector('#aliyunCaptcha-puzzle');
                        if (!p) return null;
                        return p.getBoundingClientRect().x;
                    }
                """)
                if piece_after is not None and piece_before is not None:
                    actual_move = piece_after - piece_before
                    error = target - actual_move

                    self.logger.info(
                        f"    After drag: piece moved {actual_move:.1f}px "
                        f"(target={target}px, error={error:+.1f}px)"
                    )

                    if abs(error) > 2:
                        nudge_ratio = drag_ratio
                        mouse_nudge = error / nudge_ratio

                        self.logger.info(
                            f"    Correcting: nudge mouse by {mouse_nudge:+.1f}px "
                            f"(piece error={error:+.1f}px / ratio={nudge_ratio})"
                        )

                        try:
                            slider_now = page.locator('#aliyunCaptcha-sliding-slider').bounding_box()
                            if slider_now:
                                cx = slider_now['x'] + slider_now['width'] / 2
                                cy = slider_now['y'] + slider_now['height'] / 2
                                page.mouse.move(cx + mouse_nudge, cy, steps=10)
                                time.sleep(random.uniform(0.1, 0.2))

                                piece_corrected = page.evaluate("""
                                    () => {
                                        const p = document.querySelector('#aliyunCaptcha-puzzle');
                                        if (!p) return null;
                                        return p.getBoundingClientRect().x;
                                    }
                                """)
                                if piece_corrected is not None:
                                    corrected_move = piece_corrected - piece_before
                                    new_error = target - corrected_move
                                    self.logger.info(
                                        f"    After correction: piece moved {corrected_move:.1f}px "
                                        f"(target={target}px, error={new_error:+.1f}px)"
                                    )
                        except Exception:
                            pass

                    try:
                        slider_now = page.locator('#aliyunCaptcha-sliding-slider').bounding_box()
                        if slider_now:
                            release_x = slider_now['x'] + slider_now['width'] / 2
                            release_y = slider_now['y'] + slider_now['height'] / 2
                            page.mouse.move(release_x, release_y, steps=3)
                            time.sleep(random.uniform(0.05, 0.1))
                    except Exception:
                        pass
            except Exception:
                pass

            page.mouse.up()
            time.sleep(random.uniform(0.5, 1.0))

            outcome = self._check_result(page)
            return outcome

        except Exception as e:
            self.logger.error(f"Solve error: {e}")
            return 'failed'

    def _human_scan_image(self, page: Page):
        try:
            bg = page.locator('#aliyunCaptcha-img')
            if bg.count() > 0:
                box = bg.bounding_box()
                if box:
                    scan_points = [
                        (box['x'] + box['width'] * random.uniform(0.15, 0.35),
                         box['y'] + box['height'] * random.uniform(0.20, 0.40)),
                        (box['x'] + box['width'] * random.uniform(0.60, 0.85),
                         box['y'] + box['height'] * random.uniform(0.45, 0.65)),
                    ]
                    for px, py in scan_points:
                        self.human.move_to(px, py, human=True)
                        time.sleep(random.uniform(0.05, 0.15))
            time.sleep(random.uniform(0.1, 0.3))
        except Exception:
            pass

    def _human_approach_slider(self, page: Page, box: Dict):
        viewport = page.viewport_size or {'width': 1280, 'height': 720}
        start_x = random.randint(50, viewport['width'] - 50)
        start_y = random.randint(50, viewport['height'] - 50)

        self.human.move_to(start_x, start_y, human=True)

        target_x = box['x'] + box['width'] / 2
        target_y = box['y'] + box['height'] / 2

        for _ in range(random.randint(2, 4)):
            wx = random.randint(int(target_x - 80), int(target_x + 80))
            wy = random.randint(int(target_y - 40), int(target_y + 40))
            self.human.move_to(wx, wy, human=True)
            time.sleep(random.uniform(0.05, 0.15))

        self.human.move_to(target_x, target_y, human=True, hesitate=True)

    def _human_drag(self, page: Page, box: Dict, distance: int):
        start_x = box['x'] + box['width'] / 2
        start_y = box['y'] + box['height'] / 2

        num_points = random.randint(40, 60)

        roll = random.random()
        if roll < 0.70:
            overshoot = random.uniform(3.0, 9.0)
            target_distance = distance + overshoot
            correction_kind = 'pullback'
        elif roll < 0.90:
            undershoot = random.uniform(2.0, 6.0)
            target_distance = distance - undershoot
            correction_kind = 'creep'
        else:
            overshoot = 0.0
            target_distance = distance
            correction_kind = 'none'

        drag_points: List[Tuple[float, float]] = []

        for i in range(num_points + 1):
            t = i / num_points
            eased = 1 - (1 - t) ** 3
            x = start_x + eased * target_distance
            wobble = math.sin(t * math.pi) * random.uniform(0.4, 1.2)
            y = start_y + wobble + random.uniform(-0.3, 0.3)
            drag_points.append((x, y))

        if correction_kind == 'pullback':
            drag_points.append((start_x + target_distance, start_y))
            correction_steps = random.randint(10, 18)
            for i in range(1, correction_steps + 1):
                t = i / correction_steps
                eased = t * t * (3 - 2 * t)
                x = start_x + target_distance - (overshoot * eased)
                y = start_y + random.uniform(-0.4, 0.4)
                drag_points.append((x, y))
        elif correction_kind == 'creep':
            correction_steps = random.randint(8, 14)
            for i in range(1, correction_steps + 1):
                t = i / correction_steps
                eased = t * t * (3 - 2 * t)
                x = start_x + target_distance + (undershoot * eased)
                y = start_y + random.uniform(-0.4, 0.4)
                drag_points.append((x, y))

        total_time = random.uniform(0.55, 1.05)
        step_time = total_time / num_points

        for i, (x, y) in enumerate(drag_points):
            if i < num_points:
                delay = step_time * random.uniform(0.8, 1.2)
            elif i == num_points:
                delay = random.uniform(0.05, 0.15) if correction_kind != 'none' else 0.0
            else:
                delay = random.uniform(0.02, 0.05)

            page.mouse.move(x, y)
            if delay > 0:
                time.sleep(delay)

    def _get_captcha_data(self, page: Page) -> Optional[Dict]:
        try:
            data = page.evaluate("""
                async () => {
                    const bg = document.querySelector('#aliyunCaptcha-img');
                    const puzzle = document.querySelector('#aliyunCaptcha-puzzle');
                    if (!bg || !puzzle) return null;
                    if (!bg.src || !puzzle.src) return null;

                    const bgRect = bg.getBoundingClientRect();
                    const puzzleRect = puzzle.getBoundingClientRect();

                    const fetchImage = async (url) => {
                        if (url.startsWith('data:image')) return url;
                        try {
                            const resp = await fetch(url);
                            const blob = await resp.blob();
                            return await new Promise((resolve) => {
                                const reader = new FileReader();
                                reader.onloadend = () => resolve(reader.result);
                                reader.readAsDataURL(blob);
                            });
                        } catch (e) { return null; }
                    };

                    const bg_b64 = await fetchImage(bg.src);
                    const shadow_b64 = await fetchImage(puzzle.src);
                    if (!bg_b64 || !shadow_b64) return null;

                    return {
                        bg_b64: bg_b64,
                        shadow_b64: shadow_b64,
                        bg_css_width: bgRect.width,
                        bg_natural_width: bg.naturalWidth || bg.width || 300,
                        puzzle_css_width: puzzleRect.width,
                        puzzle_natural_width: puzzle.naturalWidth || puzzle.width || 60,
                        puzzle_left_css: puzzleRect.left - bgRect.left
                    };
                }
            """)

            if not data:
                return None

            for _ in range(10):
                if (data.get('bg_natural_width', 0) > 50
                        and data.get('puzzle_natural_width', 0) > 10):
                    break
                time.sleep(0.1)
                data = page.evaluate("""
                    () => {
                        const bg = document.querySelector('#aliyunCaptcha-img');
                        const puzzle = document.querySelector('#aliyunCaptcha-puzzle');
                        if (!bg || !puzzle) return null;
                        const bgRect = bg.getBoundingClientRect();
                        const puzzleRect = puzzle.getBoundingClientRect();
                        return {
                            bg_css_width: bgRect.width,
                            bg_natural_width: bg.naturalWidth || bg.width || 300,
                            puzzle_css_width: puzzleRect.width,
                            puzzle_natural_width: puzzle.naturalWidth || puzzle.width || 60,
                            puzzle_left_css: puzzleRect.left - bgRect.left
                        };
                    }
                """)
                if not data:
                    return None

            def get_bytes(b64):
                if not b64:
                    return None
                if b64.startswith('data:image'):
                    return base64.b64decode(b64.split(',')[1])
                return base64.b64decode(b64)

            bg_bytes = get_bytes(data['bg_b64'])
            shadow_bytes = get_bytes(data['shadow_b64'])
            if not shadow_bytes or not bg_bytes:
                return None

            return {
                'shadow_bytes': shadow_bytes,
                'bg_bytes': bg_bytes,
                'bg_css_width': data['bg_css_width'],
                'bg_natural_width': data['bg_natural_width'],
                'puzzle_css_width': data['puzzle_css_width'],
                'puzzle_natural_width': data['puzzle_natural_width'],
                'puzzle_left_css': data['puzzle_left_css'],
            }
        except Exception as e:
            self.logger.debug(f"Error getting captcha data: {e}")
            return None

    def _calculate_distance_v2(self, captcha_data: Dict) -> Optional[VoteResult]:
        try:
            calc = DistanceCalculator(
                ocr=self._get_ocr(),
                logger=self.logger,
                config=self.config,
            )
            return calc.calculate(captcha_data)
        except Exception as e:
            self.logger.error(f"Distance calculation error: {e}")
            return None

    def _calculate_human_distance(self, captcha_data: Dict) -> Optional[float]:
        vote = self._calculate_distance_v2(captcha_data)
        return vote.distance if vote else None

    def _record_outcome(self, distance: float, confidence: float, success: bool):
        self._attempt_history.append((distance, confidence, success))
        if len(self._attempt_history) > 10:
            self._attempt_history.pop(0)

        if not self.config.get('enable_adaptive_offset', True):
            return

        if success:
            if self._adaptive_offset:
                self.logger.info(f"    Adaptive offset cleared (was {self._adaptive_offset:+.2f}px)")
            self._adaptive_offset = 0.0
            return

        offsets = self.config.get('calibration_offsets', [-4, -2, 0, 2, 4])
        recent_fails = 0
        for _, _, ok in reversed(self._attempt_history):
            if ok:
                break
            recent_fails += 1

        if recent_fails >= 2:
            idx = (recent_fails - 2) % len(offsets)
            new_offset = float(offsets[idx])
            if new_offset != self._adaptive_offset:
                self._adaptive_offset = new_offset
                self.logger.info(f"    Adaptive offset -> {self._adaptive_offset:+.2f}px "
                                 f"(consecutive fails: {recent_fails})")

    def _check_result(self, page: Page) -> str:
        time.sleep(random.uniform(0.5, 1.0))

        initial_url = page.url
        error_count = 0

        for poll in range(40):
            try:
                state = page.evaluate("""
                    () => {
                        if (document.querySelector('.aliyunCaptcha-verify-success'))
                            return 'success';
                        if (document.querySelector('.aliyunCaptcha-verify-error'))
                            return 'error_el';

                        const param = document.querySelector('#aliyunCaptcha-verify-param');
                        if (param && param.value && param.value.length > 20)
                            return 'success';

                        const popup = document.querySelector('#aliyunCaptcha-popup');
                        if (!popup || popup.style.display === 'none' || popup.offsetParent === null)
                            return 'popup_gone';

                        return 'pending';
                    }
                """)
                if state == 'success':
                    self.logger.info(f"    CAPTCHA success signal (poll {poll})")
                    return 'success'
                elif state == 'error_el':
                    error_count += 1
                    if error_count >= 3:
                        self.logger.info(f"    CAPTCHA failed confirmed (poll {poll}, {error_count}x error)")
                        return 'failed'
                    time.sleep(0.3)
                    continue
                elif state == 'popup_gone':
                    new_url = page.url
                    if new_url != initial_url:
                        self.logger.info(f"    Page redirected: {new_url[:80]}")
                        return 'success'
                    time.sleep(0.3)
                    new_url2 = page.url
                    if new_url2 != initial_url:
                        self.logger.info(f"    Page redirected (2nd check): {new_url2[:80]}")
                        return 'success'
                    continue
                else:
                    error_count = 0
            except Exception:
                pass
            time.sleep(0.3)

        new_url = page.url
        if new_url != initial_url:
            self.logger.info(f"    Page redirected after timeout: {new_url[:80]}")
            return 'success'

        self.logger.warning("    Result detection timed out, no redirect detected")
        return 'failed'

    def _on_success(self, page: Page) -> Optional[str]:
        self.logger.info("  Captcha solved!")
        time.sleep(0.5)
        try:
            t = page.evaluate(
                "() => { const e = document.querySelector('#aliyunCaptcha-verify-param'); return e?.value; }"
            )
            if t and len(t) > 20:
                self.logger.info(f"    Token: {t[:50]}...")
                return t
        except Exception:
            pass
        return 'success'
