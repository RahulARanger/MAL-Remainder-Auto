import random
from flask import Flask, render_template, redirect, url_for, request, abort
import requests
import pathlib
from urllib.parse import urlparse, urljoin
from concurrent.futures.thread import ThreadPoolExecutor
import webbrowser
from threading import Lock, Timer
import sys
from _thread import interrupt_main

if __name__ == "__main__":
    from common_utils import update_now_in_seconds, get_remaining_seconds, EnsurePort
    from oauth_responder import OAUTH
    from utils import get_headers, SETTINGS, force_oauth, is_there_token
    from mal_session import MALSession
    from calendar_parse import quick_save

    session = requests.Session()

root_path = pathlib.Path(__file__).parent
app = Flask(
    "Remainder Settings",
    static_folder=str(root_path / "static"),
    template_folder=str(root_path / "templates"),
)
SETTINGS_LOCK = Lock()


def ensure_settings(f):
    def ensure(*args, **kwargs):
        if SETTINGS_LOCK.locked():
            return abort(410, "Settings Lock is already Locked")

        with SETTINGS_LOCK:
            return f(*args, **kwargs)

    return ensure


def profile_pic(about_me: dict):
    url = about_me["picture"]

    save_to = (
            pathlib.Path(__file__).parent
            / "static"
            / ("Profile" + pathlib.Path(urlparse(url).path).suffix)
    )

    with save_to.open("wb") as save_as:
        response = session.get(url, stream=True)

        for chunk in response:
            save_as.write(chunk)

    about_me["picture"] = save_to.suffix

    return about_me


@app.errorhandler(404)
@app.route("/404/<failed>")
def _404(failed="Error: 404, No Page Found"):
    return render_template("404.html", name="404.html", failed=failed), 404


@app.errorhandler(410)
def _410(_):
    return render_template("410.html", name="410.html"), 410


def get_absolute_route(route):
    return urljoin(request.root_url, route)


def show_exception(message):
    return webbrowser.open(urljoin(request.url_root, "404/?failed=" + message))


class Server:
    def __init__(self):
        self.settings = SETTINGS
        self.executor = ThreadPoolExecutor(thread_name_prefix="Remainder-Server")
        self._MAL = self.mal_session() if is_there_token() else False

    def mal_session(self):
        try:
            return MALSession(session, get_headers()) if self._MAL else self._MAL
        except Exception as _:
            return ...

    def settings_page(self):
        error = [0, ""]

        try:
            ... if self.settings["id"] else self.fetch_abouts()
            expires_in, expired = get_remaining_seconds(
                int(self.settings["expires_in"]) + int(self.settings["now"])
            )
            error[0] = expires_in
            self.refresh_tokens() if expired else ...
        except Exception as _:
            error[-1] = repr(_)

        return render_template(
            "settings.html",
            name="settings.html",
            settings=self.settings,
            profile=url_for("static", filename="Profile" + self.settings["picture"]),
            error=error[-1],
            expire_time=error[0],
        )

    @ensure_settings
    def fetch_abouts(self):
        response = session.get(f"{self.settings['API']}/@me", headers=get_headers())
        response.raise_for_status()
        self.settings.from_dict(profile_pic(response.json()))

    @ensure_settings
    def refresh_tokens(self):
        response = session.post(
            f"{OAUTH}/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.settings("refresh_token"),
                "client_id": self.settings("CLIENT_ID"),
                "client_secret": self.settings("CLIENT_SECRET"),
            },
        )
        response.raise_for_status()
        self.settings.from_dict(update_now_in_seconds(response.json()))

    def update_things(self):
        try:
            watch_list = list(self.mal_session().watching())
        except Exception as error:
            return abort(404, repr(error))

        watch_list, overflown = watch_list[:-1], watch_list[-1]

        return render_template(
            "mini_board.html",
            watch_list=watch_list,
            len=len,
            reversed=reversed,
            settings=self.settings,
        )

    @ensure_settings
    def refresh(self):
        self.fetch_abouts()
        self.refresh_tokens()

    def redirect_path(self):
        raw = request.form

        try:
            quick_save(raw["calendar"]) if raw["calendar"] != self.settings["calendar"] else ...

            self.settings.from_dict(request.form)

            force_oauth() if raw["CLIENT_ID"] != self.settings["CLIENT_ID"] or raw["CLIENT_SECRET"] != \
                             self.settings["CLIENT_SECRET"] else ...

            self.refresh() if "refresh" in raw else ...

        except Exception as error:
            return abort(404, repr(error))

        return redirect("/settings")

    def update_things_in_site(self):
        form = request.form

        self.mal_session().post_changes(
            form["animes"],
            int(form["up_until"]) + int(form["watched"]),
            int(form["total"]),
        ) if (
                form.get("watched", 0)
                and "animes" in form
                and "up_until" in form
                and "total" in form
        ) else ...

        if len(sys.argv) == 2:
            # yes, it's not good practice, but since it's not meant to be used manually, it's fine this way for now.
            interrupt_main()
            return abort(410)

        return redirect("/settings")


def gen_url(_port):
    arguments = sys.argv[1:]
    arguments.append("automatic") if len(arguments) == 0 else ...
    route = "" if len(arguments) == 1 else arguments[-1]

    return f"http://localhost:{_port}/{route}"


if __name__ == "__main__":
    SERVER = Server()

    app.add_url_rule("/settings", view_func=SERVER.settings_page)
    app.add_url_rule("/save-settings", view_func=SERVER.redirect_path, methods=["POST"])

    app.add_url_rule("/", view_func=SERVER.update_things)
    app.add_url_rule("/force-scheduler", view_func=SERVER.update_things)

    app.add_url_rule(
        "/update-status", view_func=SERVER.update_things_in_site, methods=["POST"]
    )

    trust = EnsurePort("/settings")

    if trust.deep_check():
        sys.exit(0)

    port = trust()
    trust.acquire(port)

    Timer(
        random.uniform(0.69, 1),
        lambda: webbrowser.open(gen_url(port)),
    ).start()

    app.run(host="localhost", port=port, debug=False)
    trust.release()

# Reference: https://myanimelist.net/blog.php?eid=835707