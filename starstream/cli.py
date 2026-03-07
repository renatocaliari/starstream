import click
import subprocess
import sys
import os
from pathlib import Path

def detect_manager():
    if Path("uv.lock").exists() or Path("pyproject.toml").exists():
        return "uv"
    return "pip"

@click.group()
def main():
    """StarStream CLI - Real-time for StarHTML made easy."""
    pass

@main.command()
@click.argument('project_name', default='starstream-app')
def init(project_name):
    """Create a brand new StarStream project."""
    click.echo(f"🚀 Creating StarStream project: {project_name}...")
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
    click.echo(f"✅ Created {project_name}/app.py")
    click.echo(f"👉 Run: cd {project_name} && uv run app.py")

@main.command()
@click.option('--file', default='app.py', help='The file to inject StarStream into.')
def add(file):
    """Add StarStream to an EXISTING StarHTML project."""
    manager = detect_manager()
    click.echo(f"📦 Detected project manager: {manager}")
    
    # 1. Install
    if manager == "uv":
        subprocess.run(["uv", "add", "starstream"])
    else:
        subprocess.run([sys.executable, "-m", "pip", "install", "starstream"])
    
    # 2. Inject Boilerplate
    path = Path(file)
    if not path.exists():
        click.echo(f"❌ Could not find {file}. Please run in the root of your StarHTML project.")
        return

    content = path.read_text()
    if "StarStreamPlugin" in content:
        click.echo(f"ℹ️ StarStream already detected in {file}")
    else:
        click.echo(f"🔧 Injecting StarStream into {file}...")
        
        # Simple injection logic
        new_imports = "from starstream import StarStreamPlugin\n" + content
        if "app, rt = star_app()" in new_imports:
            new_content = new_imports.replace(
                "app, rt = star_app()", 
                "app, rt = star_app()\nstream = StarStreamPlugin(app, enable_history=True)"
            )
            path.write_text(new_content)
            click.echo(f"✅ Successfully integrated StarStream into {file}")
        else:
            click.echo("⚠️ Could not find 'star_app()' call. Please add 'stream = StarStreamPlugin(app)' manually.")

@main.command()
@click.argument('plugin')
def install(plugin):
    """Install extra plugins: loro, pocketbase."""
    manager = detect_manager()
    pkg = f"starstream-{plugin}"
    if manager == "uv":
        subprocess.run(["uv", "add", pkg])
    else:
        subprocess.run([sys.executable, "-m", "pip", "install", pkg])
    click.echo(f"✅ Plugin {plugin} added.")

if __name__ == "__main__":
    main()
