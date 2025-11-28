# -*- coding: utf-8 -*-
import json
import warnings
from typing import Dict, List, Optional, Union

from requests import Response

from TM1py.Exceptions import TM1pyRestException
from TM1py.Objects.Application import (
    Application,
    ApplicationTypes,
    ChoreApplication,
    CubeApplication,
    DimensionApplication,
    DocumentApplication,
    FolderApplication,
    LinkApplication,
    ProcessApplication,
    SubsetApplication,
    ViewApplication,
)
from TM1py.Services import RestService
from TM1py.Services.ObjectService import ObjectService
from TM1py.Utils import format_url, verify_version


class ApplicationService(ObjectService):
    """Service to Read and Write TM1 Applications"""

    def __init__(self, tm1_rest: RestService):
        """

        :param tm1_rest:
        """
        super().__init__(tm1_rest)
        self._rest = tm1_rest
        self._private_path_cache: Dict[str, int] = {}

    def _build_path_url(self, segments: List[str], private_from: Optional[int] = None) -> str:
        """Build URL path from segments with optional private boundary.

        :param segments: list of folder names
        :param private_from: index from which to use PrivateContents (None = all public)
        :return: URL path string for the segments
        """
        if not segments:
            return ""

        if private_from is None or private_from >= len(segments):
            return "".join(format_url("/Contents('{}')", s) for s in segments)

        if private_from <= 0:
            return "".join(format_url("/PrivateContents('{}')", s) for s in segments)

        public = "".join(format_url("/Contents('{}')", s) for s in segments[:private_from])
        private = "".join(format_url("/PrivateContents('{}')", s) for s in segments[private_from:])
        return public + private

    def _find_private_boundary(self, segments: List[str], **kwargs) -> int:
        """Find the first private folder in the path.

        Iteratively checks each segment, building the correct prefix as we go.
        Once a private folder is found, all subsequent folders are also private.

        :param segments: list of folder names
        :return: index of first private folder, or len(segments) if all public, or -1 if path doesn't exist
        """
        current_prefix = "/Contents('Applications')"

        for i, segment in enumerate(segments):
            # Use $top=0 to probe without fetching data
            public_url = current_prefix + format_url("/Contents('{}')", segment) + "?$top=0"
            try:
                self._rest.GET(public_url, **kwargs)
                current_prefix = current_prefix + format_url("/Contents('{}')", segment)
            except TM1pyRestException as e:
                if e.status_code != 404:
                    raise
                # Try private access
                private_url = current_prefix + format_url("/PrivateContents('{}')", segment) + "?$top=0"
                try:
                    self._rest.GET(private_url, **kwargs)
                    return i  # Found the first private segment
                except TM1pyRestException as e2:
                    if e2.status_code != 404:
                        raise
                    return -1  # Path doesn't exist

        return len(segments)  # All segments are public

    def _resolve_path(self, path: str, contents_suffix: str, private: bool = False, use_cache: bool = False,
                       **kwargs) -> str:
        """Resolve application path, automatically handling mixed public/private hierarchies.

        For public paths (private=False), returns direct URL without probing.
        For private paths (private=True), tries optimistic approaches first,
        falls back to iterative discovery on 404.

        :param path: path with forward slashes
        :param contents_suffix: final URL suffix (e.g., "/Contents", "/PrivateContents('name')")
        :param private: whether we're accessing private content (triggers path resolution)
        :param use_cache: whether to use/update the private boundary cache
        :return: complete URL path from Contents('Applications') to contents_suffix
        """
        base = "/Contents('Applications')"

        if not path.strip():
            return base + contents_suffix

        segments = path.split("/")

        # For public paths, just build the direct URL without probing
        if not private:
            mid = self._build_path_url(segments, None)
            return base + mid + contents_suffix

        cache_key = "/".join(segments)

        # Check cache first
        if use_cache and cache_key in self._private_path_cache:
            mid = self._build_path_url(segments, self._private_path_cache[cache_key])
            return base + mid + contents_suffix

        # Optimistic: try all-public first (most common case)
        # Use $top=0 to probe without fetching actual data
        mid_public = self._build_path_url(segments, None)
        url_public = base + mid_public + contents_suffix
        probe_url_public = url_public + ("&" if "?" in contents_suffix else "?") + "$top=0"

        try:
            self._rest.GET(probe_url_public, **kwargs)
            if use_cache:
                self._private_path_cache[cache_key] = len(segments)
            return url_public
        except TM1pyRestException as e:
            if e.status_code != 404:
                raise

        # Try all-private path
        mid_private = self._build_path_url(segments, 0)
        url_private = base + mid_private + contents_suffix
        probe_url_private = url_private + ("&" if "?" in contents_suffix else "?") + "$top=0"

        try:
            self._rest.GET(probe_url_private, **kwargs)
            if use_cache:
                self._private_path_cache[cache_key] = 0
            warnings.warn(
                f"Application path '{path}' contains private folders. "
                "Auto-resolved using PrivateContents for all segments."
            )
            return url_private
        except TM1pyRestException as e:
            if e.status_code != 404:
                raise

        # Iterative search to find the transition point
        boundary = self._find_private_boundary(segments, **kwargs)

        if boundary == -1:
            # Path genuinely doesn't exist - return original to get proper error
            return url_public

        if use_cache:
            self._private_path_cache[cache_key] = boundary

        warnings.warn(
            f"Application path '{path}' has private folder at position {boundary} ('{segments[boundary]}'). "
            "Auto-resolved using mixed Contents/PrivateContents."
        )
        mid_mixed = self._build_path_url(segments, boundary)
        return base + mid_mixed + contents_suffix

    def get_all_public_root_names(self, **kwargs):
        """
        Retrieve all public root application names.

        :param kwargs: Additional arguments for the REST request.
        :return: List of public root application names.
        """
        url = "/Contents('Applications')/Contents"
        response = self._rest.GET(url, **kwargs)
        applications = list(application["Name"] for application in response.json()["value"])
        return applications

    def get_all_private_root_names(self, **kwargs):

        url = "/Contents('Applications')/PrivateContents"
        response = self._rest.GET(url, **kwargs)
        applications = list(application["Name"] for application in response.json()["value"])
        return applications

    def get_names(self, path: str, private: bool = False, use_cache: bool = False, **kwargs):
        """Retrieve Planning Analytics Application names in given path

        Automatically handles mixed public/private folder hierarchies by discovering
        where the path transitions from public to private.

        :param path: path with forward slashes
        :param private: boolean - whether to retrieve private or public contents at the leaf
        :param use_cache: boolean - whether to cache discovered private boundaries for performance
        :return: list of application names
        """
        contents = "PrivateContents" if private else "Contents"
        url = self._resolve_path(path, "/" + contents, private, use_cache, **kwargs)

        response = self._rest.GET(url=url, **kwargs)
        return [application["Name"] for application in response.json()["value"]]

    def get(
        self, path: str, application_type: Union[str, ApplicationTypes], name: str, private: bool = False,
        use_cache: bool = False, **kwargs
    ) -> Application:
        """Retrieve Planning Analytics Application

        Automatically handles mixed public/private folder hierarchies.

        :param path: path with forward slashes
        :param application_type: str or ApplicationType from Enum
        :param name:
        :param private:
        :param use_cache: boolean - whether to cache discovered private boundaries for performance
        :return:
        """
        # raise ValueError if not a valid ApplicationType
        application_type = ApplicationTypes(application_type)

        # documents require special treatment
        if application_type == ApplicationTypes.DOCUMENT:
            return self.get_document(path=path, name=name, private=private, use_cache=use_cache, **kwargs)

        if not application_type == ApplicationTypes.FOLDER and not verify_version(
            required_version="12", version=self.version
        ):
            name += application_type.suffix

        contents = "PrivateContents" if private else "Contents"
        suffix = format_url("/" + contents + "('{}')", name)
        base_url = self._resolve_path(path, suffix, private, use_cache, **kwargs)

        if application_type == ApplicationTypes.CUBE:
            response = self._rest.GET(url=base_url + "?$expand=Cube($select=Name)", **kwargs)
            return CubeApplication(path=path, name=name, cube_name=response.json()["Cube"]["Name"])

        elif application_type == ApplicationTypes.CHORE:
            response = self._rest.GET(url=base_url + "?$expand=Chore($select=Name)", **kwargs)
            return ChoreApplication(path=path, name=name, chore_name=response.json()["Chore"]["Name"])

        elif application_type == ApplicationTypes.DIMENSION:
            response = self._rest.GET(url=base_url + "?$expand=Dimension($select=Name)", **kwargs)
            return DimensionApplication(path=path, name=name, dimension_name=response.json()["Dimension"]["Name"])

        elif application_type == ApplicationTypes.FOLDER:
            # implicit TM1pyException if application doesn't exist
            self._rest.GET(url=base_url, **kwargs)
            return FolderApplication(path=path, name=name)

        elif application_type == ApplicationTypes.LINK:
            # implicit TM1pyException if application doesn't exist
            self._rest.GET(url=base_url, **kwargs)
            response = self._rest.GET(base_url + "?$expand=*", **kwargs)
            return LinkApplication(path=path, name=name, url=response.json()["URL"])

        elif application_type == ApplicationTypes.PROCESS:
            response = self._rest.GET(url=base_url + "?$expand=Process($select=Name)", **kwargs)
            return ProcessApplication(path=path, name=name, process_name=response.json()["Process"]["Name"])

        elif application_type == ApplicationTypes.SUBSET:
            url = "".join(
                [
                    base_url,
                    "?$expand=Subset($select=Name;$expand=Hierarchy($select=Name;$expand=Dimension($select=Name)))",
                ]
            )
            response = self._rest.GET(url=url, **kwargs)
            return SubsetApplication(
                path=path,
                name=name,
                dimension_name=response.json()["Subset"]["Hierarchy"]["Dimension"]["Name"],
                hierarchy_name=response.json()["Subset"]["Hierarchy"]["Name"],
                subset_name=response.json()["Subset"]["Name"],
            )

        elif application_type == ApplicationTypes.VIEW:
            response = self._rest.GET(url=base_url + "?$expand=View($select=Name;$expand=Cube($select=Name))", **kwargs)
            return ViewApplication(
                path=path,
                name=name,
                cube_name=response.json()["View"]["Cube"]["Name"],
                view_name=response.json()["View"]["Name"],
            )

    def get_document(self, path: str, name: str, private: bool = False, use_cache: bool = False,
                      **kwargs) -> DocumentApplication:
        """Get Excel Application from TM1 Server in binary format. Can be dumped to file.

        Automatically handles mixed public/private folder hierarchies.

        :param path: path through folder structure to application. For instance: "Finance/P&L.xlsx"
        :param name: name of the application
        :param private: boolean
        :param use_cache: boolean - whether to cache discovered private boundaries for performance
        :return: Return DocumentApplication
        """
        if not name.endswith(ApplicationTypes.DOCUMENT.suffix) and not verify_version(
            required_version="12", version=self.version
        ):
            name += ApplicationTypes.DOCUMENT.suffix

        contents = "PrivateContents" if private else "Contents"
        suffix = format_url("/" + contents + "('{}')/Document/Content", name)
        url = self._resolve_path(path, suffix, private, use_cache, **kwargs)
        content = self._rest.GET(url, **kwargs).content

        suffix = format_url("/" + contents + "('{}')/Document", name)
        url = self._resolve_path(path, suffix, private, use_cache, **kwargs)
        document_fields = self._rest.GET(url, **kwargs).json()

        return DocumentApplication(
            path=path,
            name=name,
            content=content,
            file_id=document_fields.get("ID"),
            file_name=document_fields.get("Name"),
            last_updated=document_fields.get("LastUpdated"),
        )

    def delete(
        self,
        path: str,
        application_type: Union[str, ApplicationTypes],
        application_name: str,
        private: bool = False,
        use_cache: bool = False,
        **kwargs,
    ) -> Response:
        """Delete Planning Analytics application reference

        Automatically handles mixed public/private folder hierarchies.

        :param path: path through folder structure to delete the applications entry. For instance: "Finance/Reports"
        :param application_type: type of the to be deleted application entry
        :param application_name: name of the to be deleted application entry
        :param private: Access level of the to be deleted object
        :param use_cache: boolean - whether to cache discovered private boundaries for performance
        :return:
        """
        # raise ValueError if not a valid ApplicationType
        application_type = ApplicationTypes(application_type)

        if not application_type == ApplicationTypes.FOLDER and not verify_version(
            required_version="12", version=self.version
        ):
            application_name += application_type.suffix

        contents = "PrivateContents" if private else "Contents"
        suffix = format_url("/" + contents + "('{}')", application_name)
        url = self._resolve_path(path, suffix, private, use_cache, **kwargs)
        return self._rest.DELETE(url, **kwargs)

    def rename(
        self,
        path: str,
        application_type: Union[str, ApplicationTypes],
        application_name: str,
        new_application_name: str,
        private: bool = False,
        use_cache: bool = False,
        **kwargs,
    ):
        """Rename a Planning Analytics application.

        Automatically handles mixed public/private folder hierarchies.

        :param path: path through folder structure
        :param application_type: type of the application
        :param application_name: current name of the application
        :param new_application_name: new name for the application
        :param private: Access level of the object
        :param use_cache: boolean - whether to cache discovered private boundaries for performance
        :return:
        """
        # raise ValueError if not a valid ApplicationType
        application_type = ApplicationTypes(application_type)

        if not application_type == ApplicationTypes.FOLDER and not verify_version(
            required_version="12", version=self.version
        ):
            application_name += application_type.suffix

        contents = "PrivateContents" if private else "Contents"
        suffix = format_url("/" + contents + "('{}')/tm1.Move", application_name)
        url = self._resolve_path(path, suffix, private, use_cache, **kwargs)
        data = {"Name": new_application_name}

        return self._rest.POST(url, data=json.dumps(data), **kwargs)

    def create(self, application: Union[Application, DocumentApplication], private: bool = False,
               use_cache: bool = False, **kwargs) -> Response:
        """Create Planning Analytics application

        Automatically handles mixed public/private folder hierarchies.

        :param application: instance of Application
        :param private: boolean
        :param use_cache: boolean - whether to cache discovered private boundaries for performance
        :return:
        """
        contents = "PrivateContents" if private else "Contents"
        url = self._resolve_path(application.path, "/" + contents, private, use_cache, **kwargs)
        response = self._rest.POST(url, application.body, **kwargs)

        if application.application_type == ApplicationTypes.DOCUMENT:
            suffix = format_url(
                "/" + contents + "('{name}{ext}')/Document/Content",
                name=application.name,
                ext=".blob" if not verify_version(required_version="12", version=self.version) else "",
            )
            url = self._resolve_path(application.path, suffix, private, use_cache, **kwargs)
            response = self._rest.PUT(url, application.content, headers=self.binary_http_header, **kwargs)

        return response

    def update(self, application: Union[Application, DocumentApplication], private: bool = False,
               use_cache: bool = False, **kwargs) -> Response:
        """Update Planning Analytics application

        Automatically handles mixed public/private folder hierarchies.

        :param application: instance of Application
        :param private: boolean
        :param use_cache: boolean - whether to cache discovered private boundaries for performance
        :return:
        """
        contents = "PrivateContents" if private else "Contents"

        if application.application_type == ApplicationTypes.DOCUMENT:
            suffix = format_url(
                "/" + contents + "('{name}{ext}')/Document/Content",
                name=application.name,
                ext="" if verify_version("12", self.version) else ".blob"
            )
            url = self._resolve_path(application.path, suffix, private, use_cache, **kwargs)
            response = self._rest.PATCH(url=url, data=application.content, headers=self.binary_http_header, **kwargs)
        else:
            url = self._resolve_path(application.path, "/" + contents, private, use_cache, **kwargs)
            response = self._rest.POST(url, application.body, **kwargs)

        return response

    def update_or_create(
        self, application: Union[Application, DocumentApplication], private: bool = False,
        use_cache: bool = False, **kwargs
    ) -> Response:
        """Update or create Planning Analytics application

        Automatically handles mixed public/private folder hierarchies.

        :param application: instance of Application
        :param private: boolean
        :param use_cache: boolean - whether to cache discovered private boundaries for performance
        :return: Response
        """
        if self.exists(
            path=application.path,
            application_type=application.application_type,
            name=application.name,
            private=private,
            use_cache=use_cache,
            **kwargs,
        ):
            response = self.update(application=application, private=private, use_cache=use_cache, **kwargs)
        else:
            response = self.create(application=application, private=private, use_cache=use_cache, **kwargs)
        return response

    def update_or_create_document_from_file(
        self, path: str, name: str, path_to_file: str, private: bool = False, use_cache: bool = False, **kwargs
    ) -> Response:
        """Update or create application from file

        Automatically handles mixed public/private folder hierarchies.

        :param path: application path on server, i.e. 'Finance/Reports'
        :param name: name of the application on server, i.e. 'Flash.xlsx'
        :param path_to_file: full local file path of file, i.e. 'C:\\Users\\User\\Flash.xslx'
        :param private: access level of the object
        :param use_cache: boolean - whether to cache discovered private boundaries for performance
        :return: Response
        """
        if self.exists(path=path, application_type=ApplicationTypes.DOCUMENT, name=name, private=private,
                       use_cache=use_cache, **kwargs):
            response = self.update_document_from_file(
                path_to_file=path_to_file, application_path=path, application_name=name, private=private,
                use_cache=use_cache, **kwargs
            )
        else:
            response = self.create_document_from_file(
                path_to_file=path_to_file, application_path=path, application_name=name, private=private,
                use_cache=use_cache, **kwargs
            )

        return response

    def exists(
        self, path: str, application_type: Union[str, ApplicationTypes], name: str, private: bool = False,
        use_cache: bool = False, **kwargs
    ) -> bool:
        """Check if application exists

        Automatically handles mixed public/private folder hierarchies.

        :param path:
        :param application_type:
        :param name:
        :param private:
        :param use_cache: boolean - whether to cache discovered private boundaries for performance
        :return:
        """
        # raise ValueError if not a valid ApplicationType
        application_type = ApplicationTypes(application_type)

        if not application_type == ApplicationTypes.FOLDER and not verify_version(
            required_version="12", version=self.version
        ):
            name += application_type.suffix

        contents = "PrivateContents" if private else "Contents"
        suffix = format_url("/" + contents + "('{}')", name)

        # For empty path, just check directly
        if not path.strip():
            url = "/Contents('Applications')" + suffix
            return self._exists(url, **kwargs)

        segments = path.split("/")

        # For public paths, just check directly without probing
        if not private:
            mid = self._build_path_url(segments, None)
            url = "/Contents('Applications')" + mid + suffix
            return self._exists(url, **kwargs)

        # For private paths, we need path resolution
        cache_key = "/".join(segments)

        # Check cache first
        if use_cache and cache_key in self._private_path_cache:
            mid = self._build_path_url(segments, self._private_path_cache[cache_key])
            url = "/Contents('Applications')" + mid + suffix
            return self._exists(url, **kwargs)

        # Try all-public path first (most common case)
        mid_public = self._build_path_url(segments, None)
        url_public = "/Contents('Applications')" + mid_public + suffix
        if self._exists(url_public, **kwargs):
            if use_cache:
                self._private_path_cache[cache_key] = len(segments)
            return True

        # Item not found with public path - could be private folders or item doesn't exist
        # Use _find_private_boundary to check folder structure
        boundary = self._find_private_boundary(segments, **kwargs)

        if boundary == -1:
            return False  # Path doesn't exist

        if use_cache:
            self._private_path_cache[cache_key] = boundary

        mid = self._build_path_url(segments, boundary)
        url = "/Contents('Applications')" + mid + suffix
        return self._exists(url, **kwargs)

    def create_document_from_file(
        self, path_to_file: str, application_path: str, application_name: str, private: bool = False,
        use_cache: bool = False, **kwargs
    ) -> Response:
        """Create DocumentApplication in TM1 from local file

        Automatically handles mixed public/private folder hierarchies.

        :param path_to_file:
        :param application_path:
        :param application_name:
        :param private:
        :param use_cache: boolean - whether to cache discovered private boundaries for performance
        :return:
        """
        with open(path_to_file, "rb") as file:
            application = DocumentApplication(path=application_path, name=application_name, content=file.read())
            return self.create(application=application, private=private, use_cache=use_cache, **kwargs)

    def update_document_from_file(
        self, path_to_file: str, application_path: str, application_name: str, private: bool = False,
        use_cache: bool = False, **kwargs
    ) -> Response:
        """Update DocumentApplication in TM1 from local file

        Automatically handles mixed public/private folder hierarchies.

        :param path_to_file:
        :param application_path:
        :param application_name:
        :param private:
        :param use_cache: boolean - whether to cache discovered private boundaries for performance
        :return:
        """
        with open(path_to_file, "rb") as file:
            application = DocumentApplication(path=application_path, name=application_name, content=file.read())
            return self.update(application=application, private=private, use_cache=use_cache, **kwargs)
