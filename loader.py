from t4.util import BASE_PATH
from t4 import list_packages, Package
from importlib.machinery import ModuleSpec


class DataPackageLoader:

    @classmethod
    def create_module(cls, spec):
        return None

    @classmethod
    def exec_module(cls, module):
        name_parts = module.__name__.split('.')

        if module.__name__ == 't4.data':
            # __path__ must be set even if the package is virtual
            # since __path__ will be scanned by all other finders preceding this one in sys.meta_path order,
            # make sure it points to someplace short and lacking importable objects
            module.__path__ = [BASE_PATH / '.quilt' / 'named_packages']
            return module

        elif len(name_parts) == 3:  # module.__name__ == t4.data.foo
            namespace = name_parts[2]

            # we do not know the name the user will ask for ahead of time, so we must populate all valid names
            for pkg in list_packages():
                pkg_user, pkg_name = pkg.split('/')
                if pkg_user == namespace:
                    module.__dict__.update({pkg_name: Package.browse(pkg)})

            module.__path__ = [BASE_PATH / '.quilt' / 'named_packages']
            return module

        else:  # module.__name__ == t4.data.foo.bar, or a subpackage thereof: e.g. t4.data.foo.bar.baz, ...
            # There is one problem with this implementation. The following will work:
            #
            #     > from t4.data.aleksey.quilt_example import etc
            #     > from t4.data.aleksey.quilt_example.etc import imgs
            #
            # The following will not work:
            #     > from t4.data.aleksey.quilt_example.etc import imgs
            #     > from t4.data.aleksey.quilt_example import etc
            #
            # With ordinary code modules there is an assumption that if you tunnel through a name on the way to an
            # object, every name you tunnel through is a file and not an object in of itself. Passed-through names will
            # be added to the module cache as module objects. If the passed-through name is itself a data package
            # however, this will cause Python to incorrectly serve the module object instead of the package object at
            # import time.
            #
            # The solution would be to invalidate the module cache entries for the packages every time an import is
            # called (via `del sys.packages[key]`; and probably in DataPackageFinder). However, now every import would
            # import from the package definition currently on disk. This has three problems:
            # (1) importing the same package or subpackage a second time would give you a different package definition
            #     if the package manifest on disk has changed in the intervening time. This breaks user expectation,
            #      which is that importing something a second time shouldn't change anything. This is relevant in REPL
            #      environments like Jupyter, where you may run an import line many, many times.
            # (2) if the package manifest has changed on disk in the time in between importing different paths within a
            #     package, you would get served two subpackages from different versions of a package.
            # (3) this is a total hack
            #
            # My preference is to avoid cache invalidation, accept that bubbling an import up will not work, and
            # document it. You should not ordinarily need to get *less* specific with your import statements!
            namespace = name_parts[2]
            pkg_slug = name_parts[3]
            pkg_name = namespace + '/' + pkg_slug
            subpkg_names = name_parts[4:]

            pkg = Package().browse(pkg_name)

            for subpkg_name in subpkg_names:
                pkg = pkg[subpkg_name]

            for name in pkg.keys():
                module.__dict__.update({name: pkg[name]})
            module.__path__ = [BASE_PATH / '.quilt' / 'named_packages' / namespace]

            return module


class DataPackageFinder:

    @classmethod
    def find_spec(cls, fullname, path=None, target=None):
        if 't4' not in fullname:
            return None
        else:
            return ModuleSpec(fullname, DataPackageLoader())
