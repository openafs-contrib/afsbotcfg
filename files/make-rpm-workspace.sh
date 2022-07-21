#!/bin/bash
#
# Create and populate the rpmbuild directory with sources and the openafs.spec
# file.
#
# Usage:
#
#    $ cd <top-level>
#
#    $ build-tools/make-release --dir=packages HEAD
#
#    $ src/packaging/RedHat/make-rpm-workspace.sh
#
#    $ export TOPDIR=`pwd`/packages/rpmbuild
#    $ rpmbuild -ba --define "_topdir $TOPDIR" $TOPDIR/SPECS/openafs.spec
#

set -e
set -x

DIST=$(pwd)/packages              # source distribution files
AUX=src/packaging/RedHat          # auxiliary rpm packaging files
TOPDIR=$DIST/rpmbuild             # workspace to be created
SOURCES=$TOPDIR/SOURCES           # rpmbuild sources directory
SPECS=$TOPDIR/SPECS               # rpmbuild specs directory

# Determine the version strings.
# Lifted from makesrpm.pl.
version=`build-tools/git-version .`
if [[ $version =~ ([0-9.]+)(pre[0-9]+) ]]; then
    pkgver="${BASH_REMATCH[1]}"
    pkgrel="0.${BASH_REMATCH[2]}"
elif [[ "$version" =~ (.*)dev ]]; then
    pkgver="${BASH_REMATCH[1]}"
    pkgrel="0.dev";
else
    pkgver="$version"
    pkgrel="1"
fi
if [[ "$version" =~ (.*)-([0-9]+)-(g[a-f0-9]+)$ ]]; then
    if [[ "$pkgver" = "$version" ]]; then
        pkgver="${BASH_REMATCH[1]}"
    fi
    pkgrel="${pkgrel}.${BASH_REMATCH[2]}.${BASH_REMATCH[3]}";
fi
pkgver=$(echo "$pkgver" | sed 's/-/_/g')
pkgrel=$(echo "$pkgrel" | sed 's/-/_/g')

cat <<__EOF__ >.version-rpm
VERSION=${version}
PKGVER=${pkgver}
PKGREL=${pkgrel}
__EOF__


# Populate the sources directory.
mkdir -p ${SOURCES}
cp packages/openafs-${version}-src.tar.bz2 ${SOURCES}/
cp packages/openafs-${version}-doc.tar.bz2 ${SOURCES}/

cp NEWS ${SOURCES}/RELNOTES-${version}
touch ${SOURCES}/ChangeLog
cp src/afsd/CellServDB ${SOURCES}/CellServDB

cp ${AUX}/openafs-kvers-is.sh ${SOURCES}/
cp ${AUX}/openafs-buildfedora.pl ${SOURCES}/
cp ${AUX}/openafs-buildall.sh ${SOURCES}/
cp ${AUX}/openafs-kmodtool ${SOURCES}/
chmod 0755 ${SOURCES}/openafs-kvers-is.sh

# Generate the spec file.
mkdir -p ${SPECS}
sed \
  -e "s/@PACKAGE_VERSION@/${version}/g" \
  -e "s/@LINUX_PKGVER@/${pkgver}/g" \
  -e "s/@LINUX_PKGREL@/${pkgrel}/g" \
  -e "s/%define afsvers.*/%define afsvers ${version}/g" \
  -e "s/%define pkgvers.*/%define pkgvers ${pkgver}/g" \
  -e "s/^Source20:.*/Source20: CellServDB/" \
  ${AUX}/openafs.spec.in > ${SPECS}/openafs.spec
