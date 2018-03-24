#!/usr/bin/python3
"""
a basic function to check on various aspects of machine state
"""
import subprocess

def _runcmd(cmd):
    return subprocess.check_output(cmd)

def get_state(sname):
    if sname=='under_volt':
        resp=(int(_runcmd(('vcgencmd', 'get_throttled')).split(b'=')[1],0) & 1) > 0
        return resp
    elif sname=='camera_on':
        return int([ent for ent in _runcmd(('vcgencmd', 'get_camera')).split(b' ') if ent.startswith(b'detected')][0].split(b'=')[1]) > 0
    elif sname=='camera_enabled':
        return int([ent for ent in _runcmd(('vcgencmd', 'get_camera')).split(b' ') if ent.startswith(b'supported')][0].split(b'=')[1]) > 0
    return None

#0: under-voltage (0xX0001)
#1: arm frequency capped (0xX0002 or 0xX0003 with under-voltage)
#2: currently throttled (0xX0004 or 0xX0005 with under-voltage)

#16: under-voltage has occurred (0x1000X)
#17: arm frequency capped has occurred (0x2000X or 0x3000X also under-voltage occurred)
#18: throttling has occurred (0x4000X or 0x5000X also under-voltage occurred)

"""
fred=(    'vcos',
    'ap_output_control',
    'ap_output_post_processing',
    'vchi_test_init',
    'vchi_test_exit',
    'vctest_memmap',
    'vctest_start',
    'vctest_stop',
    'vctest_set',
    'vctest_get',
    'pm_set_policy',
    'pm_get_status',
    'pm_show_stats',
    'pm_start_logging',
    'pm_stop_logging',
    'version',
    'commands',
    'set_vll_dir',
    'set_backlight',
    'set_logging',
    'get_lcd_info',
    'arbiter',
    'cache_flush',
    'otp_dump',
    'test_result',
    'codec_enabled',
    'get_camera',
    'get_mem',
    'measure_clock',
    'measure_volts',
    'scaling_kernel',
    'scaling_sharpness',
    'get_hvs_asserts',
    'get_throttled',
    'measure_temp',
    'get_config',
    'hdmi_ntsc_freqs',
    'hdmi_adjust_clock',
    'hdmi_status_show',
    'hvs_update_fields',
    'pwm_speedup',
    'force_audio',
    'hdmi_stream_channels',
    'hdmi_channel_map',
    'display_power',
    'read_ring_osc',
    'memtest',
    'dispmanx_list',
    'get_rsts',
    'schmoo',
    'render_bar',
    'disk_notify',
    'inuse_notify',
    'sus_suspend',
    'sus_status',
    'sus_is_enabled',
    'sus_stop_test_thread',
    'egl_platform_switch',
    'mem_validate',
    'mem_oom',
    'mem_reloc_stats',
    'hdmi_cvt',
    'hdmi_timings',
    'file')
"""