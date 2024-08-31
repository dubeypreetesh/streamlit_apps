'''
Created on 25 Jun 2024

@author: ubuntu
'''
import threading

from chromadb.config import Settings

from decorator.synchronize import synchronized
from chromadb import AdminClient, HttpClient

class ChromaClient():
    lock = threading.Lock()
    _instances = {}
    
    def get_admin_client(self, chroma_api_impl, chroma_server_host, chroma_server_http_port):
        adminClient = AdminClient(Settings(
           chroma_api_impl=chroma_api_impl,
           chroma_server_host=chroma_server_host,
           chroma_server_http_port=chroma_server_http_port,
        ))
        return adminClient
    
    def create_tenant_if_not_exist(self, admin_client: AdminClient, tenant: str):
        try:
            admin_client.get_tenant(name=tenant)
        except Exception as e:
            admin_client.create_tenant(name=tenant)
    
    def create_database_if_not_exist(self, admin_client: AdminClient, database: str):
        try:
            admin_client.get_database(database)
        except Exception as e:
            admin_client.create_database(database)
    
    @classmethod
    @synchronized(lock)
    def get_instance(self, chroma_api_impl: str, host: str, port: int, tenant: str, database: str):
        #PERSIST_DIR is the Directory path which we also provided as "path" argument while running the chroma instance on server
        #PERSIST_DIR = str(Path.home()) + "/vector/chroma"
        admin_client = self.get_admin_client(self, chroma_api_impl=chroma_api_impl, chroma_server_host=host, chroma_server_http_port=port)
        self.create_tenant_if_not_exist(self, admin_client=admin_client, tenant=tenant)
        self.create_database_if_not_exist(self, admin_client=admin_client, database=database)
        
        key = f"{tenant}_{database}_{host}_{port}"
        if key not in self._instances:
            self._instances[key] = HttpClient(host=host, port=port, tenant=tenant, database=database)
        return self._instances[key]
        
