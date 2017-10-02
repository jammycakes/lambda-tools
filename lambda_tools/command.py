import click

@click.group()
def main():
    pass


# ====== package command ====== #

@main.command('package')
@click.argument('source_folder')
@click.argument('requirements_file')
@click.argument('target')
def package_cmd(source_folder, requirements_file, target):
    from .package import package
    package(source_folder, requirements_file, target)
