from setuptools import find_packages, setup

setup(
    name='otsuwinhdlr',
    version='2022.11.20.2',
    url='https://github.com/Otsuhachi/OtsuWinHdlr',
    description='ウィンドウやエクスプローラのハンドル取得、操作を補助します。',
    author='Otsuhachi',
    author_email='agequodagis.tufuiegoeris@gmail.com',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'otsutil',
        'otsuvalidator',
    ],
)
