# safewayClipClip

This gem of a software package will clip ALL of the coupons in your account.

To get started, create a venv and install the deps:

```
python3 -m venv safeway_venv
source safeway_venv/bin/activate
python -m pip install -r requirements/base.txt
```

To run, do something like this:

```
source safeway_venv/bin/activate
python -m safewayclipclip.cli --safeway_username=kevin@gmail.com --safeway_password=kevins_password_here
```