# coding=utf-8

import os
import platform
from contextlib import contextmanager

from conans.model.manifest import FileTreeManifest
from conans.model.package_metadata import PackageMetadata
from conans.model.ref import ConanFileReference
from conans.model.ref import PackageReference
from conans.paths import CONANFILE, SYSTEM_REQS, EXPORT_FOLDER, EXPORT_SRC_FOLDER, SRC_FOLDER, \
    BUILD_FOLDER, PACKAGES_FOLDER, SYSTEM_REQS_FOLDER, SCM_FOLDER, PACKAGE_METADATA
from conans.util.files import load, save


def short_path(func):
    if platform.system() == "Windows":
        from conans.util.windows import path_shortener

        def wrap(self, *args, **kwargs):
            p = func(self, *args, **kwargs)
            return path_shortener(p, self._short_paths)

        return wrap
    else:
        return func


class PackageCacheLayout(object):
    """ This is the package layout for Conan cache """

    def __init__(self, base_folder, ref, short_paths):
        assert isinstance(ref, ConanFileReference)
        self._ref = ref
        self._base_folder = os.path.normpath(base_folder)
        self._short_paths = short_paths

    def conan(self):
        """ Returns the base folder for this package reference """
        return self._base_folder

    def export(self):
        return os.path.join(self.conan(), EXPORT_FOLDER)

    @short_path
    def export_sources(self):
        return os.path.join(self.conan(), EXPORT_SRC_FOLDER)

    @short_path
    def source(self):
        return os.path.join(self.conan(), SRC_FOLDER)

    def conanfile(self):
        export = self.export()
        return os.path.join(export, CONANFILE)

    def builds(self):
        return os.path.join(self.conan(), BUILD_FOLDER)

    @short_path
    def build(self, pref):
        assert isinstance(pref, PackageReference)
        assert pref.ref == self._ref
        return os.path.join(self.conan(), BUILD_FOLDER, pref.id)

    def system_reqs(self):
        return os.path.join(self.conan(), SYSTEM_REQS_FOLDER, SYSTEM_REQS)

    def system_reqs_package(self, pref):
        assert isinstance(pref, PackageReference)
        assert pref.ref == self._ref
        return os.path.join(self.conan(), SYSTEM_REQS_FOLDER, pref.id, SYSTEM_REQS)

    def packages(self):
        return os.path.join(self.conan(), PACKAGES_FOLDER)

    @short_path
    def package(self, pref):
        assert isinstance(pref, PackageReference)
        assert pref.ref == self._ref
        return os.path.join(self.conan(), PACKAGES_FOLDER, pref.id)

    def scm_folder(self):
        return os.path.join(self.conan(), SCM_FOLDER)

    def package_metadata(self):
        return os.path.join(self.conan(), PACKAGE_METADATA)

    def recipe_manifest(self):
        return FileTreeManifest.load(self.export())

    def package_manifests(self, pref):
        package_folder = self.package(pref)
        readed_manifest = FileTreeManifest.load(package_folder)
        expected_manifest = FileTreeManifest.create(package_folder)
        return readed_manifest, expected_manifest

    def recipe_exists(self):
        return os.path.exists(self.export()) and \
               (not self._ref.revision or self.recipe_revision()[0] == self._ref.revision)

    def package_exists(self, pref):
        assert isinstance(pref, PackageReference)
        assert pref.ref == self._ref
        return (self.recipe_exists() and
                os.path.exists(self.package(pref)) and
                (not pref.revision or self.package_revision(pref)[0] == pref.revision))

    def recipe_revision(self):
        metadata = self.load_metadata()
        return metadata.recipe.revision, metadata.recipe.time

    def package_revision(self, pref):
        assert isinstance(pref, PackageReference)
        assert pref.ref.copy_clear_rev() == self._ref.copy_clear_rev()
        metadata = self.load_metadata()
        tm = metadata.packages[pref.id].time if metadata.packages[pref.id].time else None
        return metadata.packages[pref.id].revision, tm

    # Metadata
    def load_metadata(self):
        text = load(self.package_metadata())
        return PackageMetadata.loads(text)

    @contextmanager
    def update_metadata(self):
        try:
            metadata = self.load_metadata()
        except IOError:
            metadata = PackageMetadata()
        yield metadata
        save(self.package_metadata(), metadata.dumps())

    # Revisions
    def package_summary_hash(self, pref):
        package_folder = self.package(pref)
        readed_manifest = FileTreeManifest.load(package_folder)
        return readed_manifest.summary_hash
