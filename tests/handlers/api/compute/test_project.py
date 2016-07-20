# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 GNS3 Technologies Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
This test suite check /project endpoint
"""

import uuid
import os
import asyncio
import aiohttp
import zipfile

from unittest.mock import patch
from tests.utils import asyncio_patch

from gns3server.handlers.api.compute.project_handler import ProjectHandler
from gns3server.compute.project_manager import ProjectManager


def test_create_project_with_path(http_compute, tmpdir):
    with patch("gns3server.compute.project.Project.is_local", return_value=True):
        response = http_compute.post("/projects", {"name": "test", "path": str(tmpdir), "project_id": "00010203-0405-0607-0809-0a0b0c0d0e0f"})
        assert response.status == 201
        assert response.json["project_id"] == "00010203-0405-0607-0809-0a0b0c0d0e0f"


def test_create_project_without_dir(http_compute):
    query = {"name": "test", "project_id": "10010203-0405-0607-0809-0a0b0c0d0e0f"}
    response = http_compute.post("/projects", query, example=True)
    assert response.status == 201
    assert response.json["project_id"] == "10010203-0405-0607-0809-0a0b0c0d0e0f"
    assert response.json["name"] == "test"


def test_create_project_with_uuid(http_compute):
    query = {"name": "test", "project_id": "30010203-0405-0607-0809-0a0b0c0d0e0f"}
    response = http_compute.post("/projects", query)
    assert response.status == 201
    assert response.json["project_id"] == "30010203-0405-0607-0809-0a0b0c0d0e0f"
    assert response.json["name"] == "test"


def test_show_project(http_compute):
    query = {"name": "test", "project_id": "40010203-0405-0607-0809-0a0b0c0d0e02"}
    response = http_compute.post("/projects", query)
    assert response.status == 201
    response = http_compute.get("/projects/40010203-0405-0607-0809-0a0b0c0d0e02", example=True)
    assert len(response.json.keys()) == 2
    assert response.json["project_id"] == "40010203-0405-0607-0809-0a0b0c0d0e02"
    assert response.json["name"] == "test"


def test_show_project_invalid_uuid(http_compute):
    response = http_compute.get("/projects/50010203-0405-0607-0809-0a0b0c0d0e42")
    assert response.status == 404


def test_list_projects(http_compute):
    ProjectManager.instance()._projects = {}

    query = {"name": "test", "project_id": "51010203-0405-0607-0809-0a0b0c0d0e0f"}
    response = http_compute.post("/projects", query)
    assert response.status == 201
    query = {"name": "test", "project_id": "52010203-0405-0607-0809-0a0b0c0d0e0b"}
    response = http_compute.post("/projects", query)
    assert response.status == 201

    response = http_compute.get("/projects", example=True)
    assert response.status == 200
    assert len(response.json) == 2
    assert "51010203-0405-0607-0809-0a0b0c0d0e0f" in [p["project_id"] for p in response.json]


def test_update_path_project(http_compute, tmpdir):

    os.makedirs(str(tmpdir / "a"))
    os.makedirs(str(tmpdir / "b"))

    with patch("gns3server.compute.project.Project.is_local", return_value=True):
        response = http_compute.post("/projects", {"name": "first_name", "path": str(tmpdir / "a"), "project_id": "80010203-0405-0607-0809-0a0b0c0d0e0b"})
        assert response.status == 201
        assert response.json["name"] == "first_name"
        query = {"name": "second_name", "path": str(tmpdir / "b")}
        response = http_compute.put("/projects/{project_id}".format(project_id=response.json["project_id"]), query, example=True)
        assert response.status == 200
        assert response.json["name"] == "second_name"

        assert os.path.exists(str(tmpdir / "a"))
        assert os.path.exists(str(tmpdir / "b"))


def test_update_path_project_non_local(http_compute, tmpdir):

    with patch("gns3server.compute.project.Project.is_local", return_value=False):
        response = http_compute.post("/projects", {"name": "first_name", "project_id": "90010203-0405-0607-0809-0a0b0c0d0e0b"})
        assert response.status == 201
        query = {"name": "second_name", "path": str(tmpdir)}
        response = http_compute.put("/projects/{project_id}".format(project_id=response.json["project_id"]), query, example=True)
        assert response.status == 403


def test_delete_project(http_compute, project):
    with asyncio_patch("gns3server.compute.project.Project.delete", return_value=True) as mock:
        response = http_compute.delete("/projects/{project_id}".format(project_id=project.id), example=True)
        assert response.status == 204
        assert mock.called


def test_delete_project_invalid_uuid(http_compute):
    response = http_compute.delete("/projects/{project_id}".format(project_id=uuid.uuid4()))
    assert response.status == 404


def test_close_project(http_compute, project):
    with asyncio_patch("gns3server.compute.project.Project.close", return_value=True) as mock:
        response = http_compute.post("/projects/{project_id}/close".format(project_id=project.id), example=True)
        assert response.status == 204
        assert mock.called


def test_close_project_two_client_connected(http_compute, project):

    ProjectHandler._notifications_listening = {project.id: 2}

    with asyncio_patch("gns3server.compute.project.Project.close", return_value=True) as mock:
        response = http_compute.post("/projects/{project_id}/close".format(project_id=project.id), example=True)
        assert response.status == 204
        assert not mock.called


def test_close_project_invalid_uuid(http_compute):
    response = http_compute.post("/projects/{project_id}/close".format(project_id=uuid.uuid4()))
    assert response.status == 404


def test_get_file(http_compute, tmpdir):

    with patch("gns3server.config.Config.get_section_config", return_value={"projects_path": str(tmpdir)}):
        project = ProjectManager.instance().create_project(project_id="01010203-0405-0607-0809-0a0b0c0d0e0b")

    with open(os.path.join(project.path, "hello"), "w+") as f:
        f.write("world")

    response = http_compute.get("/projects/{project_id}/files/hello".format(project_id=project.id), raw=True)
    assert response.status == 200
    assert response.body == b"world"

    response = http_compute.get("/projects/{project_id}/files/false".format(project_id=project.id), raw=True)
    assert response.status == 404

    response = http_compute.get("/projects/{project_id}/files/../hello".format(project_id=project.id), raw=True)
    assert response.status == 403


def test_write_file(http_compute, tmpdir):

    with patch("gns3server.config.Config.get_section_config", return_value={"projects_path": str(tmpdir)}):
        project = ProjectManager.instance().create_project(project_id="01010203-0405-0607-0809-0a0b0c0d0e0b")

    response = http_compute.post("/projects/{project_id}/files/hello".format(project_id=project.id), body="world", raw=True)
    assert response.status == 200

    with open(os.path.join(project.path, "hello")) as f:
        assert f.read() == "world"

    response = http_compute.post("/projects/{project_id}/files/../hello".format(project_id=project.id), raw=True)
    assert response.status == 403


def test_stream_file(http_compute, tmpdir):

    with patch("gns3server.config.Config.get_section_config", return_value={"projects_path": str(tmpdir)}):
        project = ProjectManager.instance().create_project(project_id="01010203-0405-0607-0809-0a0b0c0d0e0b")

    with open(os.path.join(project.path, "hello"), "w+") as f:
        f.write("world")

    response = http_compute.get("/projects/{project_id}/files/hello".format(project_id=project.id), raw=True)
    assert response.status == 200
    assert response.body == b"world"

    response = http_compute.get("/projects/{project_id}/files/false".format(project_id=project.id), raw=True)
    assert response.status == 404

    response = http_compute.get("/projects/{project_id}/files/../hello".format(project_id=project.id), raw=True)
    assert response.status == 403


def test_export(http_compute, tmpdir, loop, project):

    os.makedirs(project.path, exist_ok=True)
    with open(os.path.join(project.path, 'a'), 'w+') as f:
        f.write('hello')

    response = http_compute.get("/projects/{project_id}/export".format(project_id=project.id), raw=True)
    assert response.status == 200
    assert response.headers['CONTENT-TYPE'] == 'application/gns3project'
    assert response.headers['CONTENT-DISPOSITION'] == 'attachment; filename="{}.gns3project"'.format(project.name)

    with open(str(tmpdir / 'project.zip'), 'wb+') as f:
        f.write(response.body)

    with zipfile.ZipFile(str(tmpdir / 'project.zip')) as myzip:
        with myzip.open("a") as myfile:
            content = myfile.read()
            assert content == b"hello"


def test_import(http_compute, tmpdir, loop, project):

    with zipfile.ZipFile(str(tmpdir / "test.zip"), 'w') as myzip:
        myzip.writestr("demo", b"hello")

    project_id = project.id

    with open(str(tmpdir / "test.zip"), "rb") as f:
        response = http_compute.post("/projects/{project_id}/import".format(project_id=project_id), body=f.read(), raw=True)
    assert response.status == 201

    project = ProjectManager.instance().get_project(project_id=project_id)
    with open(os.path.join(project.path, "demo")) as f:
        content = f.read()
    assert content == "hello"