CONFIG = {
    # General
    'count': 99999,
    'threads': 7,
    'headless': True, # Camoufox handles headless fine
    'timeout': 30000,
    'viewport_width': 1280,
    'viewport_height': 720,

    # Email verification poll timeout
    'verify_timeout': 90,

    # Captcha
    'max_captcha_attempts': 15,
    'result_poll_count': 60,
    'min_hole_x_native': 50,
    'template_match_threshold': 0.20,
    'distance_voting_tolerance': 5.0,
    'min_confidence_threshold': 0.0,
    'max_acceptable_spread': 30.0,
    'min_acceptable_confidence': 0.40,

    # Drag behavior
    'drag_dead_zone': 96.0,
    'drag_ratio': 1.55,

    # Adaptive offset (tweaks drag after failures)
    'enable_adaptive_offset': False,
    'calibration_offsets': [-4, -2, 2, 4, -6, 6, -8, 8],

    # Extra distance methods (experimental)
    'enable_variance_method': False,
    'enable_cv2_gray': False,
}
