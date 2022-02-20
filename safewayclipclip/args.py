import os

BASE_PATH = os.path.join(os.path.expanduser("~"), 'SafewayClipClip')


def get_name_to_help_dict(parser):
    return dict([(a.dest, a.help) for a in parser._actions])


def define_common_args(parser):
    """Parseargs shared between both CLI & GUI programs."""
    # Amazon creds:
    parser.add_argument(
        '--safeway_username', default=None,
        help=('Safeway username, either an e-mail or phone. If not provided, '
              'you will be prompted for it.'))
    parser.add_argument(
        '--safeway_user_will_login',
        action='store_true',
        default=False,
        help='If set, let the user log in on their own.')

    default_session_path = os.path.join(BASE_PATH, 'ChromeSession')
    parser.add_argument(
        '--session-path', nargs='?',
        default=default_session_path,
        help=('Directory to save browser session, including cookies. Use to '
              'prevent repeated MFA prompts. Defaults to a directory in your '
              'home dir. Set to None to use a temporary profile.'))
    parser.add_argument(
        '--headless',
        action='store_true',
        default=False,
        help='Whether to execute chromedriver with no visible window.')

    parser.add_argument(
        '-V', '--version', action='store_true',
        help='Shows the app version and quits.')
