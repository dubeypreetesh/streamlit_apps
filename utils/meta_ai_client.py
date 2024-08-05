'''
Created on 03-Jul-2024

@author: ongraph
'''
import threading

from meta_ai_api import MetaAI

from decorator.synchronize import synchronized


class MetaAIClient():
    lock = threading.Lock()
    _instances = {}
    
    @classmethod
    @synchronized(lock)
    def get_instance(self, fb_email, fb_password):
        if fb_email not in self._instances:
            self._instances[fb_email] = MetaAI(fb_email, fb_password)
        return self._instances[fb_email]
