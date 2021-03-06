# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os.path
import random

from libcloud.common.types import LibcloudError

from libcloud.storage.base import Object, Container, StorageDriver
from libcloud.storage.types import ContainerAlreadyExistsError
from libcloud.storage.types import ContainerDoesNotExistError
from libcloud.storage.types import ContainerIsNotEmptyError
from libcloud.storage.types import ObjectDoesNotExistError


class DummyFileObject(file):
    def __init__(self, yield_count=5, chunk_len=10):
        self._yield_count = yield_count
        self._chunk_len = chunk_len

    def read(self, size):
        i = 0

        while i < self._yield_count:
            yield self._get_chunk(self._chunk_len)
            i += 1

        raise StopIteration

    def _get_chunk(self, chunk_len):
        chunk = [str(x) for x in random.randint(97, 120)]
        return chunk

    def __len__(self):
        return self._yield_count * self._chunk_len

class DummyIterator(object):
    def __init__(self, data=None):
        self._data = data or []
        self._current_item = 0

    def next(self):
        if self._current_item == len(self._data):
            raise StopIteration

        value = self._data[self._current_item]
        self._current_item += 1
        return value

# @@FIX: the doctests below are not run by the main test suite
class DummyStorageDriver(StorageDriver):
    """
    Dummy Storage driver.

    >>> from libcloud.storage.drivers.dummy import DummyStorageDriver
    >>> driver = DummyStorageDriver('key', 'secret')
    >>> container = driver.create_container(container_name='test container')
    >>> container
    <Container: name=test container, provider=Dummy Storage Provider>
    >>> container.name
    'test container'
    >>> container.extra['object_count']
    0
    """

    name = 'Dummy Storage Provider'

    def __init__(self, api_key, api_secret):
        self._containers = {}

    def get_meta_data(self):
        """
        >>> driver = DummyStorageDriver('key', 'secret')
        >>> driver.get_meta_data()
        {'object_count': 0, 'container_count': 0, 'bytes_used': 0}
        >>> container = driver.create_container(container_name='test container 1')
        >>> container = driver.create_container(container_name='test container 2')
        >>> obj = container.upload_object_via_stream(
        ...  object_name='test object', iterator=DummyFileObject(5, 10), extra={})
        >>> driver.get_meta_data()
        {'object_count': 1, 'container_count': 2, 'bytes_used': 50}
        """

        container_count = len(self._containers)
        object_count = sum([ len(self._containers[container]['objects']) for
                        container in self._containers ])

        bytes_used = 0
        for container in self._containers:
            objects = self._containers[container]['objects']
            for _, obj in objects.iteritems():
                bytes_used += obj.size

        return { 'container_count': int(container_count),
                  'object_count': int(object_count),
                  'bytes_used': int(bytes_used) }

    def list_containers(self):
        """
        >>> driver = DummyStorageDriver('key', 'secret')
        >>> driver.list_containers()
        []
        >>> container = driver.create_container(container_name='test container 1')
        >>> container
        <Container: name=test container 1, provider=Dummy Storage Provider>
        >>> container.name
        'test container 1'
        >>> container = driver.create_container(container_name='test container 2')
        >>> container
        <Container: name=test container 2, provider=Dummy Storage Provider>
        >>> container = driver.create_container(
        ...  container_name='test container 2') #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        ContainerAlreadyExistsError:
        >>> container_list=driver.list_containers()
        >>> sorted([container.name for container in container_list])
        ['test container 1', 'test container 2']
        """

        return [container['container'] for container in
                self._containers.values()]

    def list_container_objects(self, container):
        container = self.get_container(container.name)

        return container.objects

    def get_container(self, container_name):
        """
        >>> driver = DummyStorageDriver('key', 'secret')
        >>> driver.get_container('unknown') #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        ContainerDoesNotExistError:
        >>> container = driver.create_container(container_name='test container 1')
        >>> container
        <Container: name=test container 1, provider=Dummy Storage Provider>
        >>> container.name
        'test container 1'
        >>> driver.get_container('test container 1')
        <Container: name=test container 1, provider=Dummy Storage Provider>
        """

        if container_name not in self._containers:
            raise ContainerDoesNotExistError(driver=self, value=None,
                                             container_name=container_name)

        return self._containers[container_name]['container']

    def get_object(self, container_name, object_name):
        """
       >>> driver = DummyStorageDriver('key', 'secret')
       >>> driver.get_object('unknown', 'unknown') #doctest: +IGNORE_EXCEPTION_DETAIL
       Traceback (most recent call last):
       ContainerDoesNotExistError:
       >>> container = driver.create_container(container_name='test container 1')
       >>> container
       <Container: name=test container 1, provider=Dummy Storage Provider>
       >>> driver.get_object(
       ...  'test container 1', 'unknown') #doctest: +IGNORE_EXCEPTION_DETAIL
       Traceback (most recent call last):
       ObjectDoesNotExistError:
       >>> obj = container.upload_object_via_stream(object_name='test object',
       ...      iterator=DummyFileObject(5, 10), extra={})
       >>> obj
       <Object: name=test object, size=50, hash=None, provider=Dummy Storage Provider ...>
        """

        self.get_container(container_name)

        container_objects = self._containers[container_name]['objects']
        if object_name not in container_objects:
            raise ObjectDoesNotExistError(object_name=object_name, value=None,
                                          driver=self)

        return container_objects[object_name]

    def create_container(self, container_name):
        """
        >>> driver = DummyStorageDriver('key', 'secret')
        >>> container = driver.create_container(container_name='test container 1')
        >>> container
        <Container: name=test container 1, provider=Dummy Storage Provider>
        >>> container = driver.create_container(
        ...    container_name='test container 1') #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        ContainerAlreadyExistsError:
        """

        if container_name in self._containers:
            raise ContainerAlreadyExistsError(container_name=container_name,
                                              value=None, driver=self)

        extra = { 'object_count': 0 }
        container = Container(name=container_name, extra=extra, driver=self)

        self._containers[container_name] = { 'container': container,
                                             'objects': {}
                                           }
        return container

    def delete_container(self, container):
        """
        >>> driver = DummyStorageDriver('key', 'secret')
        >>> container = Container(name = 'test container',
        ...    extra={'object_count': 0}, driver=driver)
        >>> driver.delete_container(container=container)#doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        ContainerDoesNotExistError:
        >>> container = driver.create_container(
        ...      container_name='test container 1') #doctest: +IGNORE_EXCEPTION_DETAIL
        >>> len(driver._containers)
        1
        >>> driver.delete_container(container=container)
        True
        >>> len(driver._containers)
        0
        >>> container = driver.create_container(
        ...    container_name='test container 1') #doctest: +IGNORE_EXCEPTION_DETAIL
        >>> obj = container.upload_object_via_stream(
        ...   object_name='test object', iterator=DummyFileObject(5, 10), extra={})
        >>> driver.delete_container(container=container)#doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        ContainerIsNotEmptyError:
        """

        container_name = container.name
        if container_name not in self._containers:
            raise ContainerDoesNotExistError(container_name=container_name,
                                             value=None, driver=self)

        container = self._containers[container_name]
        if len(container['objects']) > 0:
            raise ContainerIsNotEmptyError(container_name=container_name,
                                           value=None, driver=self)

        del self._containers[container_name]
        return True

    def download_object(self, obj, destination_path, overwrite_existing=False,
                       delete_on_failure=True):
        kwargs_dict =  {'obj': obj,
                        'response': DummyFileObject(),
                        'destination_path': destination_path,
                        'overwrite_existing': overwrite_existing,
                        'delete_on_failure': delete_on_failure}

        return self._save_object(**kwargs_dict)

    def download_object_as_stream(self, obj, chunk_size=None):
        """
        >>> driver = DummyStorageDriver('key', 'secret')
        >>> container = driver.create_container(
        ...   container_name='test container 1') #doctest: +IGNORE_EXCEPTION_DETAIL
        >>> obj = container.upload_object_via_stream(object_name='test object',
        ...    iterator=DummyFileObject(5, 10), extra={})
        >>> stream = container.download_object_as_stream(obj)
        >>> stream #doctest: +ELLIPSIS
        <closed file '<uninitialized file>', mode '<uninitialized file>' at 0x...>
        """

        return DummyFileObject()

    def upload_object(self, file_path, container, object_name, extra=None,
                      file_hash=None):
        """
        >>> driver = DummyStorageDriver('key', 'secret')
        >>> container = driver.create_container(container_name='test container 1')
        >>> container.upload_object(file_path='/tmp/inexistent.file',
        ...     object_name='test') #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        LibcloudError:
        >>> file_path = path = os.path.abspath(__file__)
        >>> file_size = os.path.getsize(file_path)
        >>> obj = container.upload_object(file_path=file_path, object_name='test')
        >>> obj #doctest: +ELLIPSIS
        <Object: name=test, size=...>
        >>> obj.size == file_size
        True
        """

        if not os.path.exists(file_path):
            raise LibcloudError(value='File %s does not exist' % (file_path),
                                driver=self)

        size = os.path.getsize(file_path)
        return self._add_object(container=container, object_name=object_name,
                                size=size, extra=extra)

    def upload_object_via_stream(self, iterator, container,
                                 object_name, extra=None):
        """
        >>> driver = DummyStorageDriver('key', 'secret')
        >>> container = driver.create_container(
        ...    container_name='test container 1') #doctest: +IGNORE_EXCEPTION_DETAIL
        >>> obj = container.upload_object_via_stream(
        ...   object_name='test object', iterator=DummyFileObject(5, 10), extra={})
        >>> obj #doctest: +ELLIPSIS
        <Object: name=test object, size=50, ...>
        """

        size = len(iterator)
        return self._add_object(container=container, object_name=object_name,
                                size=size, extra=extra)

    def delete_object(self, obj):
        """
        >>> driver = DummyStorageDriver('key', 'secret')
        >>> container = driver.create_container(
        ...   container_name='test container 1') #doctest: +IGNORE_EXCEPTION_DETAIL
        >>> obj = container.upload_object_via_stream(object_name='test object',
        ...   iterator=DummyFileObject(5, 10), extra={})
        >>> obj #doctest: +ELLIPSIS
        <Object: name=test object, size=50, ...>
        >>> container.delete_object(obj=obj)
        True
        >>> obj = Object(name='test object 2',
        ...    size=1000, hash=None, extra=None,
        ...    meta_data=None, container=container,driver=None)
        >>> container.delete_object(obj=obj) #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        ObjectDoesNotExistError:
        """

        container_name = obj.container.name
        object_name = obj.name
        obj = self.get_object(container_name=container_name,
                              object_name=object_name)

        del self._containers[container_name]['objects'][object_name]
        return True

    def _add_object(self, container, object_name, size, extra=None):
        container = self.get_container(container.name)

        extra = extra or {}
        meta_data = extra.get('meta_data', {})
        obj = Object(name=object_name, size=size, extra=extra, hash=None,
                     meta_data=meta_data, container=container, driver=self)

        self._containers[container.name]['objects'][object_name] = obj
        return obj

if __name__ == "__main__":
    import doctest
    doctest.testmod()
