"""A Python script to build the Verible package for a given platform"""

# This script is called from the github build workflow and runs
# in the repo's top dir. It uses _upstream and _packages dirs
# for input and output respectivly.


import os
import json
import subprocess
from dataclasses import dataclass
from typing import List, Union
import argparse
import shutil
from pathlib import Path

# -- Command line options.
parser = argparse.ArgumentParser()


# The platform id. E.g. "darwin-arm64"
parser.add_argument("--platform-id", required=True, type=str, help="Platform to build")


# Path to the properties file with the build info.
parser.add_argument(
    "--build-info-json", required=True, type=str, help="JSON with build properties"
)

args = parser.parse_args()


def run(cmd_args: Union[List[str], str], shell: bool = False) -> None:
    """Run a command and check that it succeeded. Select shell=true to enable
    shell features such as '*' glob."""
    print(f"\nRun: {cmd_args}", flush=True)
    print(f"{shell=}", flush=True)
    subprocess.run(cmd_args, check=True, shell=shell)
    print("Run done\n", flush=True)


@dataclass(frozen=True)
class PlatformInfo:
    """Represents the properties of a platform."""

    verible_base_filename: str
    verible_ext: str
    # The name of the wrapper dir when uncompressing Verible package.
    verible_wrapper_dir: str
    unarchive_cmd: str


def get_platform_info(platform_id: str, verible_release_tag: str) -> PlatformInfo:
    """Extract (platform_id, platform_info)"""
    platforms = {
        "darwin-arm64": PlatformInfo(
            f"verible-{verible_release_tag}-macOS",
            "tar.gz",
            f"verible-{verible_release_tag}-macOS",
            ["tar", "zxf"],
        ),
        "darwin-x86-64": PlatformInfo(
            f"verible-{verible_release_tag}-macOS",
            "tar.gz",
            f"verible-{verible_release_tag}-macOS",
            ["tar", "zxf"],
        ),
        "linux-x86-64": PlatformInfo(
            f"verible-{verible_release_tag}-linux-static-x86_64",
            "tar.gz",
            f"verible-{verible_release_tag}",
            ["tar", "zxf"],
        ),
        "linux-aarch64": PlatformInfo(
            f"verible-{verible_release_tag}-linux-static-arm64",
            "tar.gz",
            f"verible-{verible_release_tag}",
            ["tar", "zxf"],
        ),
        "windows-amd64": PlatformInfo(
            f"verible-{verible_release_tag}-win64",
            "zip",
            f"verible-{verible_release_tag}-win64",
            ["unzip"],
        ),
    }

    return platforms[platform_id]


def main():
    """Builds the Apio oss-cad-suite package for one platform."""

    # -- Save the start dir. It is assume to be at top of this repo.
    work_dir: Path = Path.cwd()
    print(f"\n{work_dir=}")

    # -- Get platform id.
    platform_id = args.platform_id
    print(f"{platform_id=}")

    # -- Get the build info
    with Path(args.build_info_json).open("r", encoding="utf-8") as f:
        build_info = json.load(f)

    print("\nOriginal build info:")
    print(json.dumps(build_info, indent=2))

    # -- Determine if processing the windows package.
    is_windows = "windows" in platform_id
    print(f"\n{is_windows=}")

    # -- Extract build info params
    release_tag = build_info["release-tag"]
    package_tag = release_tag.replace("-", "")
    verible_release_tag = build_info["verible-release-tag"]
    # verible_package_tag = verible_release_tag.replace("-", "")
    platform_info = get_platform_info(platform_id, verible_release_tag)

    print()
    print(f"* {platform_id=}")
    print(f"* {release_tag=}")
    print(f"* {package_tag=}")
    print(f"* {platform_info=}")
    print(f"* {verible_release_tag=}")

    # --  Create folder for storing the upstream packages
    upstream_dir: Path = work_dir / "_upstream" / platform_id
    print(f"\n{upstream_dir=}")
    upstream_dir.mkdir(parents=True, exist_ok=True)

    # -- Create folder for storing the generated package file.
    package_dir: Path = work_dir / "_packages" / platform_id
    print(f"\n{package_dir=}")
    package_dir.mkdir(parents=True, exist_ok=True)

    # -- Construct target package file name
    parts = [
        "apio-verible",
        "-",
        platform_id,
        "-",
        package_tag,
        ".tgz",
    ]
    package_filename = "".join(parts)
    print(f"\n{package_filename=}")
    build_info["target-platform"] = platform_id
    build_info["file-name"] = package_filename

    # Construct verible file name
    verible_fname = (
        platform_info.verible_base_filename + "." + platform_info.verible_ext
    )
    print(f"\n{verible_fname=}")

    # -- Construct Verible URL
    parts = [
        "https://github.com/chipsalliance/verible/releases/download",
        "/",
        verible_release_tag,
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

    # -- Write updated build info to the package
    print("Writing package build info.")
    output_json_file = package_dir / "BUILD-INFO.json"
    with output_json_file.open("w", encoding="utf-8") as f:
        json.dump(build_info, f, indent=2)
        f.write("\n")  # Ensure the file ends with a newline
    run(["cat", "-n", output_json_file])

    # -- Format the json file in the package dir
    print("Formatting package build info.")
    # -- This tool is installed by the workflow as part of the
    # -- format-json-file action.
    run(["json-align", "--in-place", "--spaces", "2", output_json_file])
    run(["cat", "-n", output_json_file])

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
