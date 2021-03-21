import setuptools
from distutils.core import setup

with open('README.md', encoding="utf-8") as f:
    readme = f.read()

setup(
    name="wrtview",
    version="0.11.0",
    description="Network information viewer for OpenWRT",
    long_description=readme,
    long_description_content_type='text/markdown',
    url="https://github.com/ropg/wrtview",
    author="Rop Gonggrijp",
    license="MIT",
    classifiers=["Development Status :: 3 - Alpha",
                 "Programming Language :: Python :: 3"],
    keywords="openwrt, networking",
    project_urls={
        "Documentation": "https://github.com/ropg/wrtview/blob/master/README.md",
        "Source": "https://github.com/ropg/wrtview",
        "Tracker": "https://github.com/ropg/wrtview/issues",
    },
    packages=["wrtview"],
    python_requires=">=3.5",
    setup_requires=["wheel"],
    install_requires=[],
    entry_points={
        "console_scripts": [
            # command = package.module:function
            "wrtview = wrtview.wrtview:main",
        ],
    },
    package_data={"wrtview": ["vendors"]},
)
