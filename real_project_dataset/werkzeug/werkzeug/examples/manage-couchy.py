import click
from werkzeug.serving import run_simple


def make_app():
    from couchy.application import Couchy

    return Couchy("http://localhost:5984")


def make_shell():
    from couchy import models, utils

    application = make_app()
    return {"application": application, "models": models, "utils": utils}


@click.group()
def cli():
    pass


@cli.command()
def initdb():
    from couchy.application import Couchy

    Couchy("http://localhost:5984").init_database()


@cli.command()
@click.option("-h", "--hostname", type=str, default="localhost", help="localhost")
@click.option("-p", "--port", type=int, default=5000, help="5000")
@click.option("--no-reloader", is_flag=True, default=False)
@click.option("--debugger", is_flag=True)
@click.option("--no-evalex", is_flag=True, default=False)
@click.option("--threaded", is_flag=True)
@click.option("--processes", type=int, default=1, help="1")
def runserver(hostname, port, no_reloader, debugger, no_evalex, threaded, processes):
    app = make_app()
    reloader = not no_reloader
    evalex = not no_evalex
    run_simple(
        hostname,
        port,
        app,
        use_reloader=reloader,
        use_debugger=debugger,
        use_evalex=evalex,
        threaded=threaded,
        processes=processes,
    )


@cli.command()
@click.option("--no-ipython", is_flag=True, default=False)
def shell(no_ipython):
    banner = "Interactive Werkzeug Shell"
    namespace = make_shell()
    if not no_ipython:
        try:
            try:
                from IPython.frontend.terminal.embed import InteractiveShellEmbed

                sh = InteractiveShellEmbed.instance(banner1=banner)
            except ImportError:
                from IPython.Shell import IPShellEmbed

                sh = IPShellEmbed(banner=banner)
        except ImportError:
            pass
        else:
            sh(local_ns=namespace)
            return
    from code import interact

    interact(banner, local=namespace)


if __name__ == "__main__":
    cli()
