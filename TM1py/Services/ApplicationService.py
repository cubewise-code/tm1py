# -*- coding: utf-8 -*-
import json
from typing import Dict, List, Optional, Tuple, Union

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

    def _build_path_url(self, segments: List[str], private_boundary: Optional[int] = None) -> str:
        """Build URL path from segments with optional private boundary.

        :param segments: list of folder names
        :param private_boundary: index from which to use PrivateContents (None = all public)
        :return: URL path string for the segments
        """
        if not segments:
            return ""

        # All public
        if private_boundary is None or private_boundary >= len(segments):
            return "".join(format_url("/Contents('{}')", s) for s in segments)

        # All private
        if private_boundary <= 0:
            return "".join(format_url("/PrivateContents('{}')", s) for s in segments)

        # Mixed: public up to boundary, then private
        public_part = "".join(format_url("/Contents('{}')", s) for s in segments[:private_boundary])
        private_part = "".join(format_url("/PrivateContents('{}')", s) for s in segments[private_boundary:])
        return public_part + private_part

    def _find_private_boundary(self, segments: List[str], **kwargs) -> int:
        """Find the first private folder in the path.

        Iteratively checks each segment to find where the path transitions
        from public to private. Once a private folder is found, all subsequent
        folders are also private (TM1 rule).

        :param segments: list of folder names
        :return: index of first private folder, or len(segments) if all public, or -1 if path doesn't exist
        """
        current_prefix = "/Contents('Applications')"

        for i, segment in enumerate(segments):
            # Try public access first
            public_url = current_prefix + format_url("/Contents('{}')", segment) + "?$top=0"
            try:
                self._rest.GET(public_url, **kwargs)
                # Segment is public, continue building prefix
                current_prefix = current_prefix + format_url("/Contents('{}')", segment)
            except TM1pyRestException as e:
                if e.status_code != 404:
                    raise
                # Not found as public, try private
                private_url = current_prefix + format_url("/PrivateContents('{}')", segment) + "?$top=0"
                try:
                    self._rest.GET(private_url, **kwargs)
                    return i  # Found the first private segment
                except TM1pyRestException as e2:
                    if e2.status_code != 404:
                        raise
                    return -1  # Path doesn't exist

        return len(segments)  # All segments are public

    def _resolve_path(self, path: str, private: bool = False, use_cache: bool = False, **kwargs) -> Tuple[str, bool]:
        """Resolve application path, handling mixed public/private folder hierarchies.

        For public access (private=False), returns direct URL without probing.
        For private access (private=True), probes to find where private folders begin.

        :param path: path with forward slashes (e.g., "Planning Sample/Reports")
        :param private: whether we're accessing private content (triggers path probing)
        :param use_cache: whether to use/update the private boundary cache
        :return: tuple of (resolved_base_url, in_private_context)
                 - resolved_base_url: URL from Contents('Applications') through the path
                 - in_private_context: True if any folder in path is private
        """
        base = "/Contents('Applications')"

        if not path.strip():
            return base, False

        segments = path.split("/")

        # For public access, assume all-public path (no probing needed)
        if not private:
            mid = self._build_path_url(segments, None)
            return base + mid, False

        # For private access, we need to find where private folders begin
        cache_key = "/".join(segments)

        # Check cache first
        if use_cache and cache_key in self._private_path_cache:
            boundary = self._private_path_cache[cache_key]
            mid = self._build_path_url(segments, boundary)
            in_private_context = boundary < len(segments)
            return base + mid, in_private_context

        # Optimistic: try all-public first (common case)
        mid_public = self._build_path_url(segments, None)
        url_public = base + mid_public
        try:
            self._rest.GET(url_public + "?$top=0", **kwargs)
            if use_cache:
                self._private_path_cache[cache_key] = len(segments)
            return url_public, False
        except TM1pyRestException as e:
            if e.status_code != 404:
                raise

        # Optimistic: try all-private
        mid_private = self._build_path_url(segments, 0)
        url_private = base + mid_private
        try:
            self._rest.GET(url_private + "?$top=0", **kwargs)
            if use_cache:
                self._private_path_cache[cache_key] = 0
            return url_private, True
        except TM1pyRestException as e:
            if e.status_code != 404:
                raise

        # Iterative search to find the exact transition point
        boundary = self._find_private_boundary(segments, **kwargs)

        if boundary == -1:
            # Path doesn't exist - return public URL to get proper error message
            return url_public, False

        if use_cache:
            self._private_path_cache[cache_key] = boundary

        mid = self._build_path_url(segments, boundary)
        in_private_context = boundary < len(segments)
        return base + mid, in_private_context

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
        """
        Retrieve all private root application names.

        :param kwargs: Additional arguments for the REST request.
        :return: List of private root application names.
        """
        url = "/Contents('Applications')/PrivateContents"
        response = self._rest.GET(url, **kwargs)
        applications = list(application["Name"] for application in response.json()["value"])
        return applications

    def get_names(self, path: str, private: bool = False, use_cache: bool = False, **kwargs):
        """Retrieve Planning Analytics Application names in given path

        Automatically handles mixed public/private folder hierarchies.

        :param path: path with forward slashes
        :param private: boolean - whether to retrieve private or public contents at the leaf
        :param use_cache: boolean - whether to cache discovered private boundaries
        :return: list of application names
        """
        base_url, in_private_context = self._resolve_path(path, private, use_cache, **kwargs)

        # Use PrivateContents if we're in a private context OR if private=True
        contents = "PrivateContents" if (private or in_private_context) else "Contents"
        url = base_url + "/" + contents

        response = self._rest.GET(url=url, **kwargs)
        return [application["Name"] for application in response.json()["value"]]

    def get(
        self,
        path: str,
        application_type: Union[str, ApplicationTypes],
        name: str,
        private: bool = False,
        use_cache: bool = False,
        **kwargs,
    ) -> Application:
        """Retrieve Planning Analytics Application

        Automatically handles mixed public/private folder hierarchies.

        :param path: path with forward slashes
        :param application_type: str or ApplicationType from Enum
        :param name:
        :param private:
        :param use_cache: boolean - whether to cache discovered private boundaries
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

        base_url, in_private_context = self._resolve_path(path, private, use_cache, **kwargs)

        # Use PrivateContents if we're in a private context OR if private=True
        contents = "PrivateContents" if (private or in_private_context) else "Contents"
        base_url = format_url(base_url + "/" + contents + "('{}')", name)

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

    def get_document(
        self, path: str, name: str, private: bool = False, use_cache: bool = False, **kwargs
    ) -> DocumentApplication:
        """Get Excel Application from TM1 Server in binary format. Can be dumped to file.

        Automatically handles mixed public/private folder hierarchies.

        :param path: path through folder structure to application. For instance: "Finance/P&L.xlsx"
        :param name: name of the application
        :param private: boolean
        :param use_cache: boolean - whether to cache discovered private boundaries
        :return: Return DocumentApplication
        """
        if not name.endswith(ApplicationTypes.DOCUMENT.suffix) and not verify_version(
            required_version="12", version=self.version
        ):
            name += ApplicationTypes.DOCUMENT.suffix

        base_url, in_private_context = self._resolve_path(path, private, use_cache, **kwargs)

        # Use PrivateContents if we're in a private context OR if private=True
        contents = "PrivateContents" if (private or in_private_context) else "Contents"

        url = format_url(base_url + "/" + contents + "('{}')/Document/Content", name)
        content = self._rest.GET(url, **kwargs).content

        url = format_url(base_url + "/" + contents + "('{}')/Document", name)
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
        :param use_cache: boolean - whether to cache discovered private boundaries
        :return:
        """
        # raise ValueError if not a valid ApplicationType
        application_type = ApplicationTypes(application_type)

        if not application_type == ApplicationTypes.FOLDER and not verify_version(
            required_version="12", version=self.version
        ):
            application_name += application_type.suffix

        base_url, in_private_context = self._resolve_path(path, private, use_cache, **kwargs)

        # Use PrivateContents if we're in a private context OR if private=True
        contents = "PrivateContents" if (private or in_private_context) else "Contents"
        url = format_url(base_url + "/" + contents + "('{}')", application_name)

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
        :param use_cache: boolean - whether to cache discovered private boundaries
        :return:
        """
        # raise ValueError if not a valid ApplicationType
        application_type = ApplicationTypes(application_type)

        if not application_type == ApplicationTypes.FOLDER and not verify_version(
            required_version="12", version=self.version
        ):
            application_name += application_type.suffix

        base_url, in_private_context = self._resolve_path(path, private, use_cache, **kwargs)

        # Use PrivateContents if we're in a private context OR if private=True
        contents = "PrivateContents" if (private or in_private_context) else "Contents"
        url = format_url(base_url + "/" + contents + "('{}')/tm1.Move", application_name)

        data = {"Name": new_application_name}
        return self._rest.POST(url, data=json.dumps(data), **kwargs)

    def create(
        self,
        application: Union[Application, DocumentApplication],
        private: bool = False,
        use_cache: bool = False,
        **kwargs,
    ) -> Response:
        """Create Planning Analytics application

        Automatically handles mixed public/private folder hierarchies.

        :param application: instance of Application
        :param private: boolean
        :param use_cache: boolean - whether to cache discovered private boundaries
        :return:
        """
        base_url, in_private_context = self._resolve_path(application.path, private, use_cache, **kwargs)

        # Use PrivateContents if we're in a private context OR if private=True
        contents = "PrivateContents" if (private or in_private_context) else "Contents"
        url = base_url + "/" + contents

        response = self._rest.POST(url, application.body, **kwargs)

        if application.application_type == ApplicationTypes.DOCUMENT:
            url = format_url(
                base_url + "/" + contents + "('{name}{suffix}')/Document/Content",
                name=application.name,
                suffix=".blob" if not verify_version(required_version="12", version=self.version) else "",
            )
            response = self._rest.PUT(url, application.content, headers=self.binary_http_header, **kwargs)

        return response

    def update(
        self,
        application: Union[Application, DocumentApplication],
        private: bool = False,
        use_cache: bool = False,
        **kwargs,
    ) -> Response:
        """Update Planning Analytics application

        Automatically handles mixed public/private folder hierarchies.

        :param application: instance of Application
        :param private: boolean
        :param use_cache: boolean - whether to cache discovered private boundaries
        :return:
        """
        base_url, in_private_context = self._resolve_path(application.path, private, use_cache, **kwargs)

        # Use PrivateContents if we're in a private context OR if private=True
        contents = "PrivateContents" if (private or in_private_context) else "Contents"

        if application.application_type == ApplicationTypes.DOCUMENT:
            url = format_url(
                base_url + "/" + contents + "('{name}{extension}')/Document/Content",
                name=application.name,
                extension="" if verify_version("12", self.version) else ".blob",
            )
            response = self._rest.PATCH(url=url, data=application.content, headers=self.binary_http_header, **kwargs)
        else:
            url = base_url + "/" + contents
            response = self._rest.POST(url, application.body, **kwargs)

        return response

    def update_or_create(
        self,
        application: Union[Application, DocumentApplication],
        private: bool = False,
        use_cache: bool = False,
        **kwargs,
    ) -> Response:
        """Update or create Planning Analytics application

        Automatically handles mixed public/private folder hierarchies.

        :param application: instance of Application
        :param private: boolean
        :param use_cache: boolean - whether to cache discovered private boundaries
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
        :param use_cache: boolean - whether to cache discovered private boundaries
        :return: Response
        """
        if self.exists(
            path=path,
            application_type=ApplicationTypes.DOCUMENT,
            name=name,
            private=private,
            use_cache=use_cache,
            **kwargs,
        ):
            response = self.update_document_from_file(
                path_to_file=path_to_file,
                application_path=path,
                application_name=name,
                private=private,
                use_cache=use_cache,
                **kwargs,
            )
        else:
            response = self.create_document_from_file(
                path_to_file=path_to_file,
                application_path=path,
                application_name=name,
                private=private,
                use_cache=use_cache,
                **kwargs,
            )

        return response

    def exists(
        self,
        path: str,
        application_type: Union[str, ApplicationTypes],
        name: str,
        private: bool = False,
        use_cache: bool = False,
        **kwargs,
    ) -> bool:
        """Check if application exists

        Automatically handles mixed public/private folder hierarchies.

        :param path:
        :param application_type:
        :param name:
        :param private:
        :param use_cache: boolean - whether to cache discovered private boundaries
        :return:
        """
        # raise ValueError if not a valid ApplicationType
        application_type = ApplicationTypes(application_type)

        if not application_type == ApplicationTypes.FOLDER and not verify_version(
            required_version="12", version=self.version
        ):
            name += application_type.suffix

        # For exists check with private=True, we need special handling
        # because we want to check both public and private paths
        if not private:
            # Simple public check
            segments = path.split("/") if path.strip() else []
            mid = self._build_path_url(segments, None)
            url = "/Contents('Applications')" + mid + "/Contents('" + name + "')"
            return self._exists(url, **kwargs)

        # For private access, first try to resolve the path
        segments = path.split("/") if path.strip() else []

        if not segments:
            # Root level - just check directly
            url = "/Contents('Applications')/PrivateContents('" + name + "')"
            return self._exists(url, **kwargs)

        # Check cache first
        cache_key = "/".join(segments)
        if use_cache and cache_key in self._private_path_cache:
            boundary = self._private_path_cache[cache_key]
            mid = self._build_path_url(segments, boundary)
            in_private_context = boundary < len(segments)
            contents = "PrivateContents" if in_private_context else "Contents"
            url = "/Contents('Applications')" + mid + "/" + contents + "('" + name + "')"
            return self._exists(url, **kwargs)

        # Try all-public path first
        mid_public = self._build_path_url(segments, None)
        url_public = "/Contents('Applications')" + mid_public + "/PrivateContents('" + name + "')"
        if self._exists(url_public, **kwargs):
            if use_cache:
                self._private_path_cache[cache_key] = len(segments)
            return True

        # Try to find the private boundary
        boundary = self._find_private_boundary(segments, **kwargs)

        if boundary == -1:
            return False  # Path doesn't exist

        if use_cache:
            self._private_path_cache[cache_key] = boundary

        mid = self._build_path_url(segments, boundary)
        # If path has private folders, item must be accessed via PrivateContents
        contents = "PrivateContents" if boundary < len(segments) else "PrivateContents"
        url = "/Contents('Applications')" + mid + "/" + contents + "('" + name + "')"
        return self._exists(url, **kwargs)

    def create_document_from_file(
        self,
        path_to_file: str,
        application_path: str,
        application_name: str,
        private: bool = False,
        use_cache: bool = False,
        **kwargs,
    ) -> Response:
        """Create DocumentApplication in TM1 from local file

        Automatically handles mixed public/private folder hierarchies.

        :param path_to_file:
        :param application_path:
        :param application_name:
        :param private:
        :param use_cache: boolean - whether to cache discovered private boundaries
        :return:
        """
        with open(path_to_file, "rb") as file:
            application = DocumentApplication(path=application_path, name=application_name, content=file.read())
            return self.create(application=application, private=private, use_cache=use_cache, **kwargs)

    def update_document_from_file(
        self,
        path_to_file: str,
        application_path: str,
        application_name: str,
        private: bool = False,
        use_cache: bool = False,
        **kwargs,
    ) -> Response:
        """Update DocumentApplication in TM1 from local file

        Automatically handles mixed public/private folder hierarchies.

        :param path_to_file:
        :param application_path:
        :param application_name:
        :param private:
        :param use_cache: boolean - whether to cache discovered private boundaries
        :return:
        """
        with open(path_to_file, "rb") as file:
            application = DocumentApplication(path=application_path, name=application_name, content=file.read())
            return self.update(application=application, private=private, use_cache=use_cache, **kwargs)

    def _extract_type_from_odata(self, odata_type: str) -> str:
        """Extract the type name from @odata.type string.

        :param odata_type: e.g., '#ibm.tm1.api.v1.Folder'
        :return: e.g., 'Folder'
        """
        if odata_type and "." in odata_type:
            return odata_type.split(".")[-1]
        return odata_type or "Unknown"

    def _get_contents_raw(self, path: str, private: bool, in_private_context: bool, **kwargs) -> List[Dict]:
        """Get raw contents from API for a given path.

        :param path: the path to query
        :param private: whether to access private contents
        :param in_private_context: whether we're already in a private context
        :return: list of raw item dictionaries from API
        """
        base = "/Contents('Applications')"

        if not path.strip():
            # Root level
            url = base + ("/PrivateContents" if private else "/Contents")
        else:
            # Need to properly resolve the path to handle mixed public/private hierarchies
            if in_private_context or private:
                # Find the actual private boundary in the path
                segments = path.split("/")
                boundary = self._find_private_boundary(segments, **kwargs)
                if boundary == -1:
                    # Path doesn't exist
                    return []
                mid = self._build_path_url(segments, boundary)
            else:
                # All public path
                segments = path.split("/")
                mid = self._build_path_url(segments, None)

            contents = "PrivateContents" if (private or in_private_context) else "Contents"
            url = base + mid + "/" + contents

        try:
            response = self._rest.GET(url, **kwargs)
            return response.json().get("value", [])
        except TM1pyRestException as e:
            if e.status_code == 404:
                return []
            raise

    def _discover_at_path(
        self,
        path: str,
        include_private: bool,
        recursive: bool,
        flat: bool,
        in_private_context: bool,
        results: List[Dict],
        **kwargs,
    ) -> List[Dict]:
        """Discover items at a specific path, handling both public and private contents.

        :param path: current path being explored
        :param include_private: whether to include private assets
        :param recursive: whether to recurse into folders
        :param flat: whether to return flat list
        :param in_private_context: whether we're in a private folder context (everything below is private)
        :param results: accumulator for flat mode
        :return: list of discovered items
        """
        items = []

        if in_private_context:
            # Inside a private folder - everything is private, only one call needed
            raw_items = self._get_contents_raw(path, private=True, in_private_context=True, **kwargs)
            self._process_items(
                raw_items=raw_items,
                path=path,
                is_private=True,
                in_private_context=True,
                include_private=include_private,
                recursive=recursive,
                flat=flat,
                results=results,
                items=items,
                **kwargs,
            )
        else:
            # Public context - get public contents
            raw_public = self._get_contents_raw(path, private=False, in_private_context=False, **kwargs)
            self._process_items(
                raw_items=raw_public,
                path=path,
                is_private=False,
                in_private_context=False,
                include_private=include_private,
                recursive=recursive,
                flat=flat,
                results=results,
                items=items,
                **kwargs,
            )

            # Also get private contents if requested (private items in a public folder)
            if include_private:
                raw_private = self._get_contents_raw(path, private=True, in_private_context=False, **kwargs)
                self._process_items(
                    raw_items=raw_private,
                    path=path,
                    is_private=True,
                    in_private_context=False,
                    include_private=include_private,
                    recursive=recursive,
                    flat=flat,
                    results=results,
                    items=items,
                    **kwargs,
                )

        return items if not flat else results

    def _process_items(
        self,
        raw_items: List[Dict],
        path: str,
        is_private: bool,
        in_private_context: bool,
        include_private: bool,
        recursive: bool,
        flat: bool,
        results: List[Dict],
        items: List[Dict],
        **kwargs,
    ):
        """Process raw items from API and handle recursion.

        :param raw_items: raw items from API
        :param path: current path
        :param is_private: whether these items are private
        :param in_private_context: whether we're in a private folder context
        :param include_private: whether to include private assets
        :param recursive: whether to recurse into folders
        :param flat: whether to return flat list
        :param results: accumulator for flat mode
        :param items: accumulator for nested mode
        """
        for raw_item in raw_items:
            odata_type = raw_item.get("@odata.type", "")
            item_type = self._extract_type_from_odata(odata_type)
            item_name = raw_item.get("Name", "")
            item_id = raw_item.get("ID", "")

            # Build full path for this item
            item_path = f"{path}/{item_name}" if path else item_name

            item = {
                "@odata.type": odata_type,
                "type": item_type,
                "id": item_id,
                "name": item_name,
                "path": item_path,
                "is_private": is_private or in_private_context,
            }

            # Handle recursion for folders
            if recursive and item_type == "Folder":
                # When recursing into a private folder, everything below is private
                new_private_context = is_private or in_private_context
                children = self._discover_at_path(
                    path=item_path,
                    include_private=include_private,
                    recursive=recursive,
                    flat=flat,
                    in_private_context=new_private_context,
                    results=results,
                    **kwargs,
                )
                if not flat:
                    item["children"] = children

            if flat:
                results.append(item)
            else:
                items.append(item)

    def discover(
        self, path: str = "", include_private: bool = False, recursive: bool = False, flat: bool = False, **kwargs
    ) -> List[Dict]:
        """Discover applications in the Applications folder.

        Traverses the application hierarchy and returns information about all
        discovered items including folders, documents, views, and other references.

        :param path: starting path (empty string = root 'Applications' folder)
        :param include_private: whether to include private assets in the results
        :param recursive: whether to recurse into subfolders
        :param flat: if True, returns a flat list; if False (default), returns nested structure
        :return: list of dictionaries with keys: @odata.type, type, id, name, path, is_private
                 - @odata.type: full OData type (e.g., '#ibm.tm1.api.v1.Folder')
                 - type: simplified type name (e.g., 'Folder')
                 For nested mode, folders also have a 'children' key when recursive=True
        """
        results = []  # Accumulator for flat mode

        # Determine if we're starting in a private context (path contains private folders)
        in_private_context = False
        if path.strip() and include_private:
            _, in_private_context = self._resolve_path(path, private=True, use_cache=False, **kwargs)

        # Use the unified discovery method
        items = self._discover_at_path(
            path=path,
            include_private=include_private,
            recursive=recursive,
            flat=flat,
            in_private_context=in_private_context,
            results=results,
            **kwargs,
        )

        return results if flat else items
