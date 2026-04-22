import os
import logging
import threading
from inotify_simple import INotify,flags
import time
from collections import defaultdict

class FileFlux():
  """Track files in directory for flux"""
  def __init__(self,path):
    logging.basicConfig(format='%(asctime)s %(message)s',level=logging.DEBUG)
    self.inotify = INotify() #init tracker object
    self.path = path #path of dir to be trackex
    self.tracked_dirs = {} # paths tracked with watch descriptor attached
    self.running_thread = None
    self.new_save = False
    self.lock = threading.Lock()
    self.event_timers = defaultdict(str)
  
  
  def record_close(self):
    with self.lock:
      self.new_save = True
      logging.info("closed file")
      
  def handle_events(self,events):
    for event in events:
        logging.info(f"{event.name},{flags.from_mask(event.mask)}")
        
        if event.mask & flags.CLOSE_WRITE:
          logging.info(f"Change detected")
          #coalesce signals so we get one notification
          with self.lock:
            old = self.event_timers.get(event.name)
            if old:
              old.cancel()
          
          t = threading.Timer(1,self.record_close)
          
          self.event_timers[event.name] = t
          t.start()
          
                    
        elif event.mask & flags.CREATE and event.mask & flags.ISDIR:
          logging.info(f"New dir detected:{event.name}\n Adding Tracker")
          self.add_tracker()
    
  def start_watcher(self):
    """Start a thread to watch for file flux"""
    if self.running_thread:
      logging.info("Running event watcher active")
      return
    try:
      event_thread = threading.Thread(target=self.event_thread,daemon = True)
      event_thread.start()
      self.running_thread = event_thread
      event_thread.join()
    except Exception as e:
      logging.exception(e)
    
  def add_tracker(self):
    """Add tracker and get watch descriptor for each dir and its contents"""
    for dir, sub_dir, file in os.walk(self.path):
      #self.path_util(dir,file)
      if dir not in self.tracked_dirs:
        try:
          wd = self.inotify.add_watch(dir,flags.CREATE | flags.DELETE | flags.MODIFY | flags.CLOSE_WRITE | flags.ATTRIB | flags.MOVED_FROM | flags.MOVED_TO)
          logging.info(f"Tracking changes in :{dir}")
          self.tracked_dirs[dir] = wd
        except Exception as e:
          logging.error("Failed to add tracker  to dir:{dir}")
  
  def event_thread(self):
    """Start tracking file change events"""
    self.add_tracker()
    while True:
      events = self.inotify.read()
      self.handle_events(events)
      
                
if  __name__ == "__main__":
    fileflux = FileFlux(os.getcwd())
    fileflux.start_watcher()
                    