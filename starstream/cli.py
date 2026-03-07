import click
import subprocess
import sys
from pathlib import Path

@click.group()
def main():
    """StarStream CLI - Real-time for StarHTML made easy."""
    pass

@main.command()
@click.argument('project_name', default='starstream-app')
def init(project_name):
    """Initialize a new StarStream project with zero-config."""
    click.echo(f"🚀 Creating StarStream project: {project_name}...")
    
    # Create basic structure
    Path(project_name).mkdir(exist_ok=True)
    app_py = Path(project_name) / "app.py"
    
    if not app_py.exists():
        app_py.write_text("""from starhtml import *
from starstream import StarStreamPlugin

app, rt = star_app()
stream = StarStreamPlugin(app, enable_history=True)

@rt("/")
def index():
    return Container(
        H1("StarStream App"),
        stream.get_stream_element(topic="global"),
        Div(id="chat"),
        Form(
            Input(name="msg", placeholder="Type a message..."),
            Button("Send"),
            hx_post="/send", hx_target="#chat", hx_swap="none"
        )
    )

@rt("/send")
@sse
async def send(msg: str):
    yield elements(Div(msg), "#chat", "append")

serve()
""")
        click.echo(f"✅ Created {app_py}")
    
    click.echo("\nTo run your app:")
    click.echo(f"  cd {project_name}")
    click.echo("  uv run app.py")

@main.command()
@click.argument('plugin_name')
def install(plugin_name):
    """Install a StarStream plugin (loro, pocketbase)."""
    full_name = f"starstream-{plugin_name}"
    click.echo(f"📦 Installing plugin: {full_name}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", full_name])
        click.echo(f"✅ Plugin {plugin_name} installed successfully.")
    except Exception as e:
        click.echo(f"❌ Error installing plugin: {e}", err=True)

if __name__ == "__main__":
    main()
