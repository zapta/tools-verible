#!/bin/bash
#############################################
#   Apio Verible package builder            #
#############################################

# -- Set the version the generated apio package
VERSION="0.0.1"

# -- Set the version of the upstream release.
# -- See list at https://github.com/chipsalliance/verible/releases
VERSION_SRC="v0.0-3862-g936dfb1d"

# -- For debugging, echo executed commands.
#set -x

# -- Exit on any error
set -e

# -- Set english language for propper pattern matching
export LC_ALL=C

# -- The name of the generated apio package.
#NAME=verible

# -- This version is stored in a temporal file so that
# -- github actions can read it and figure out the package
# -- name for upload it to the new release
echo "$VERSION" > "VERSION_BUILD"

# -- Base URL for oss-cad-suite package
SRC_URL_BASE="https://github.com/chipsalliance/verible/releases/download"

# -- Show the packaged version
echo "Package  version: ${VERSION}"
echo "Upstream version: ${VERSION_SRC}"

# -- Target architectures
ARCH=$1
TARGET_ARCHS="linux_x86_64 linux_aarch64 windows_amd64 darwin darwin_arm64"

# -- Print the help message and exit
function print_help_exit {
  echo ""
  echo "Usage: bash build.sh ARCHITECTURE"
  echo ""
  echo "ARCHITECTURES: ${TARGET_ARCHS}"
  echo ""
  echo "Example:"
  echo "bash build.sh linux_x86_64"
  echo ""
  exit 1
}

# ----------------------------------
# --- Check the Script parameters
# -----------------------------------

# --- There should be only one parameter
if [[ $# -ne 1 ]]; then
  echo ""
  echo "Error: expecting exacly one argument, found $#"
  print_help_exit
fi

# -- There sould be one parameter: The target architecture
# -- If no parameter, show an error message
#if [[ $# -lt 1 ]]; then
#  echo ""
#  echo "Error: No target architecture given"
#  print_help_exit
#fi

# -- Check that the architectur name is correct is supported
#if [[ $ARCH =~ [[:space:]] || ! $TARGET_ARCHS =~ (^|[[:space:]])$ARCH([[:space:]]|$) ]]; then
#  echo ""
#  echo ">>> WRONG ARCHITECTURE \"$ARCH\""
#  print_help_exit
#fi

echo ""
echo "******* Building tools-$NAME apio package"
# echo ">>> ARCHITECTURE \"$ARCH\""
echo ""
echo "* ARCH:"
echo "  $ARCH"

# ---------------------------------------------------------------------
# - Create the folders to use for downloading the upstreams package
# - and creating the packages
# ---------------------------------------------------------------------

# -- Save the current dir
WORK_DIR=$PWD

# --  Folder for storing the upstream packages
UPSTREAM_DIR=$WORK_DIR/_upstream/$ARCH

# -- Folder for storing the generated packages
PACKAGE_DIR=$WORK_DIR/_packages/$ARCH

# -- Create the upstream directory 
mkdir -p "$UPSTREAM_DIR"

# -- Create the packages directory
mkdir -p $PACKAGE_DIR

echo ""
echo "* UPSTREAM DIR:"
echo "  $UPSTREAM_DIR"
echo ""
echo "* PACKAGE DIR:"
echo "  $PACKAGE_DIR"
echo ""


# -- Map apio arch to verible source arch.

if [ "${ARCH}" == "linux_x86_64" ]; then
   ARCH_SRC="linux-static-x86_64"
   EXT_SRC="tar.gz"
   TOP_DIR_SRC="verible-${VERSION_SRC}"

elif [ "${ARCH}" == "linux_aarch64" ]; then
   ARCH_SRC="linux-static-arm64"
   EXT_SRC="tar.gz"
   TOP_DIR_SRC="verible-${VERSION_SRC}"

elif [ "${ARCH}" == "windows_amd64" ]; then
   ARCH_SRC="win64"
   EXT_SRC="zip"
   TOP_DIR_SRC="verible-${VERSION_SRC}-${ARCH_SRC}"

elif [ "${ARCH}" == "darwin" ]; then
   ARCH_SRC="macOS"
   EXT_SRC="tar.gz"
   TOP_DIR_SRC="verible-${VERSION_SRC}-${ARCH_SRC}"

elif [ "${ARCH}" == "darwin_arm64" ]; then
   ARCH_SRC="macOS"
   EXT_SRC="tar.gz"
   TOP_DIR_SRC="verible-${VERSION_SRC}-${ARCH_SRC}"

else
  echo ""
  echo "Error: unknown arch argument [${ARCH}."
  print_help_exit
fi

# -- The name of the upstream file, with extension.
FILENAME_SRC="verible-${VERSION_SRC}-${ARCH_SRC}.${EXT_SRC}"

echo "* Upstream package name:"
echo "  $FILENAME_SRC"
echo ""

# --------------------------------------------------
# ---- DOWNLOAD THE UPSTREAM oss-cad-suite PACKAGE
# --------------------------------------------------

# -- Construct download url.
SRC_URL=${SRC_URL_BASE}/${VERSION_SRC}/${FILENAME_SRC}

echo "---> Downloading upstream OSS-CAD-SUITE package."
echo ""
echo "* URL: "
echo "  $SRC_URL"

# -- Change to the upstream folder. This is the destination of the 
# -- download operation.
cd "$UPSTREAM_DIR"

# -- Download the source package (non verbose)
# -- If it has not already downloaded yet
test -e $FILENAME_SRC || wget -nv $SRC_URL

# --- Uncompress the upstream file.
echo ""
echo "---> Extracting the upstream OSS-CAD-SUITE package."

# -- On windows platforms we use 7z, as it is an self-extract .exe file
if [ "${ARCH:0:7}" == "windows" ]; then
  unzip $FILENAME_SRC

else
  # -- tar for the other platforms
  tar vzxf $FILENAME_SRC
fi

# -- clean upstream file to save local disk space,
#rm -f $FILENAME_SRC

# -- Construct the target file name.
#PACKAGE_NAME=tools-verible-$ARCH-$VERSION
PACKAGE_FILE_NAME="tools-verible-${ARCH}-${VERSION}.tar.gz"

# Make the package dir.

# Copy files from upstream to package.
echo $UPSTREAM_DIR

if [ "${ARCH}" == "windows_amd64" ]; then
  # -- The upstream windows package is lacking the 'bin' directory.
  mkdir -p ${PACKAGE_DIR}/content/bin
  cp -r ${UPSTREAM_DIR}/${TOP_DIR_SRC}/* ${PACKAGE_DIR}/content/bin
else
  mkdir -p ${PACKAGE_DIR}/content
  cp -r ${UPSTREAM_DIR}/${TOP_DIR_SRC}/* ${PACKAGE_DIR}/content
fi

# -- Copy templates/package-template.json and fill-in version and arch.
# -- Using in-place flag with an actual ".bak" suffix for OSX compatibilty.
echo "---> Setting target package metadata."
PACKAGE_JSON=$PACKAGE_DIR/content/package.json
cp -r "$WORK_DIR"/build-data/package-template.json $PACKAGE_JSON
sed -i.bak "s/%VERSION%/\"$VERSION\"/;" $PACKAGE_JSON
sed -i.bak "s/%SYSTEM%/\"$ARCH\"/;" $PACKAGE_JSON
sed -i.bak "s/%UPSTREAM_VERSION%/\"$VERSION_SRC\"/;" $PACKAGE_JSON
rm ${PACKAGE_JSON}.bak


# -- Copy the license file.
cp $WORK_DIR/build-data/verible-license.txt $PACKAGE_DIR/content/LICENSE.txt

# -- Compress the package dir.
echo ""
echo "---> Compressing the target package."
cd ${PACKAGE_DIR}/content
echo $PWD
tar zcf ../../${PACKAGE_FILE_NAME} * 


# -- All done.
echo ""
echo "--> Package file created: $PACKAGE_DIR/$PACKAGE_FILE_NAME"
