"""A Python script to build the Verible package for a given platform"""

# This script is called from the github build workflow.


import os
import subprocess
from dataclasses import dataclass
from typing import List
import argparse
import shutil
from pathlib import Path

# -- Command line options.
parser = argparse.ArgumentParser()


parser.add_argument("--platform_id", required=True, type=str, help="Platform to build")
parser.add_argument(
    "--package-tag", required=True, type=str, help="Package file name tag"
)
parser.add_argument(
    "--build-info-file", required=True, type=str, help="Text file with build properties"
)

args = parser.parse_args()


# -- Set the version of the upstream release.
# -- See list at https://github.com/chipsalliance/verible/releases
VERIBLE_TAG = "v0.0-3862-g936dfb1d"


def run(cmd_args: Union[List[str], str], shell: bool = False) -> None:
    """Run a command and check that it succeeded. Select shell=true to enable
    shell features such as '*' glob."""
    print(f"\nRun: {cmd_args}")
    print(f"{shell=}")
    subprocess.run(cmd_args, check=True, shell=shell)
    print("Run done\n")


@dataclass(frozen=True)
class PlatformInfo:
    """Represents the properties of a platform."""

    verible_base_filename: str
    verible_ext: str
    # The name of the wrapper dir when uncompressing Verible package.
    verible_wrapper_dir: str
    unarchive_cmd: str


# -- Maps apio platform codes to their attributes.
PLATFORMS = {
    "darwin-arm64": PlatformInfo(
        f"verible-{VERIBLE_TAG}-macOS",
        "tar.gz",
        f"verible-{VERIBLE_TAG}-macOS",
        ["tar", "zxf"],
    ),
    "darwin-x86-64": PlatformInfo(
        f"verible-{VERIBLE_TAG}-macOS",
        "tar.gz",
        f"verible-{VERIBLE_TAG}-macOS",
        ["tar", "zxf"],
    ),
    "linux-x86-64": PlatformInfo(
        f"verible-{VERIBLE_TAG}-linux-static-x86_64",
        "tar.gz",
        f"verible-{VERIBLE_TAG}",
        ["tar", "zxf"],
    ),
    "linux-aarch64": PlatformInfo(
        f"verible-{VERIBLE_TAG}-linux-static-arm64",
        "tar.gz",
        f"verible-{VERIBLE_TAG}",
        ["tar", "zxf"],
    ),
    "windows-amd64": PlatformInfo(
        f"verible-{VERIBLE_TAG}-win64",
        "zip",
        f"verible-{VERIBLE_TAG}-win64",
        ["unzip"],
    ),
}


def main():
    """Builds the Apio oss-cad-suite package for one platform."""

    # pylint: disable=too-many-statements

    # -- Print build parameters
    print("Apio oss-cad-suite builder")

    print("\nPARAMS:")
    print(f"  Platform ID:       {args.platform_id}")
    print(f"  Verible tag:       {VERIBLE_TAG}")
    print(f"  Package tag:       {args.package_tag}")
    print(f"  Build info file:   {args.build_info_file}")

    # -- Map to Verible platform info
    platform_info = PLATFORMS[args.platform_id]
    print(f"\n{platform_info=}")

    # -- Determine if processing the windows package.
    is_windows = "windows" in args.platform_id
    print(f"\n{is_windows=}")

    # -- Save the start dir. It is assume to be at top of this repo.
    work_dir: Path = Path.cwd()
    print(f"\n{work_dir=}")

    # -- Save absolute build info file path
    build_info_path = Path(args.build_info_file).absolute()
    print(f"{build_info_path=}")
    assert build_info_path.exists()
    assert build_info_path.is_file()

    # --  Folder for storing the upstream packages
    upstream_dir: Path = work_dir / "_upstream" / args.platform_id
    print(f"\n{upstream_dir=}")
    upstream_dir.mkdir(parents=True, exist_ok=True)

    # -- Folder for storing the generated package file.
    package_dir: Path = work_dir / "_packages" / args.platform_id
    print(f"\n{package_dir=}")
    package_dir.mkdir(parents=True, exist_ok=True)

    # -- Construct target package file name
    parts = [
        "apio-verible",
        "-",
        args.platform_id,
        "-",
        args.package_tag,
        ".tar.gz",
    ]
    package_filename = "".join(parts)
    print(f"\n{package_filename=}")

    # Construct verible file name
    verible_fname = (
        platform_info.verible_base_filename + "." + platform_info.verible_ext
    )
    print(f"\n{verible_fname=}")

    # -- Construct Verible URL
    parts = [
        "https://github.com/chipsalliance/verible/releases/download",
        "/",
        VERIBLE_TAG,
        "/",
        verible_fname,
    ]
    verible_url = "".join(parts)
    print(f"\n{verible_url=}")

    # -- Download the Verible file.
    print(f"\nChanging to UPSTREAM_DIR: {str(upstream_dir)}")
    os.chdir(upstream_dir)
    print(f"\nDownloading {verible_url}")
    run(["wget", "-nv", verible_url])
    run(["ls", "-al"])

    # -- Uncompress the Verible archive
    print("Uncompressing the Verible file")
    run(platform_info.unarchive_cmd + [verible_fname])
    run(["ls", "-al"])

    # -- Delete the Verible archive, we don't need it anymore
    print("Deleting the Verible archive file")
    Path(verible_fname).unlink()
    run(["ls", "-al"])

    # -- Determine the root dir of the Verible files, below the
    # -- wrapper dir.
    print(f"\n{Path.cwd()=}")
    verible_root = Path(platform_info.verible_wrapper_dir)
    print(f"{verible_root=}")
    print(f"{verible_root.absolute()=}")
    if is_windows:
        # -- Windows package has no 'bin' dir.
        assert (verible_root / "verible-verilog-format.exe").is_file()
    else:
        assert (verible_root / "bin").is_dir()

    # -- Copy the package files to the output directory.
    # -- We use rsync to copy all, including sim links, if any.
    # -- The does "/" matters.
    print("\nCopying package files.")
    # -- For windows, inset the missing 'bin' dir.
    dst = package_dir / "bin" if is_windows else package_dir
    run(["rsync", "-aq", f"{verible_root}/", f"{dst}/"])

    # -- Delete the upstream dir
    print(f"\nDeleting upstream dir {verible_root}")
    shutil.rmtree(verible_root)

    # -- Add to the the build info file and append platform info.
    package_build_info = package_dir / "BUILD-INFO"
    run(["cp", build_info_path, package_build_info])
    with package_build_info.open("a") as f:
        f.write(f"platform-id = {args.platform_id}\n")
        f.write(f"verible-tag = {VERIBLE_TAG}\n")
    run(["ls", "-al", package_dir])
    run(["cat", "-n", package_build_info])

    # print("Compressing the  package.")
    # os.chdir(package_dir)
    # print(f"{Path.cwd()=}")
    # # -- The flag 'q' is for 'quiet'.
    # zip_cmd = f"zip -qr ../{package_filename} *"
    # subprocess.run(zip_cmd, shell=True, check=True)

    # -- Compress the package. We run in a shell for the '*' glob to expand.
    print("Compressing the  package.")
    os.chdir(package_dir)
    run(f"tar zcf ../{package_filename} ./*", shell=True)

    # -- Delete the package dir
    print(f"\nDeleting package dir {package_dir}")
    shutil.rmtree(package_dir)

    # -- Final check
    os.chdir(work_dir)
    print(f"{Path.cwd()=}")
    run(["ls", "-al"])
    run(["ls", "-al", "_packages"])
    assert (Path("_packages") / package_filename).is_file()

    # -- All done


if __name__ == "__main__":
    main()
