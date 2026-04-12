import os
import logging
import threading
from inotify_simple import INotify,flags
from collections import defaultdict

class FileFlux():
  """Track files in directory for flux"""
  def __init__(self,path):
    logging.basicConfig(format='%(asctime)s %(message)s',level=logging.DEBUG)
    self.inotify = INotify() #init tracker object
    self.path = path #path of dir to be trackex
    self.tracked_dirs = {} # paths tracked with watch descriptor attached
    self.running_thread = None
    self.mtimes = defaultdict(dict)
  
  def path_join(self, dir_s, file_s):
    return os.path.join(dir_s, file_s)
    
  def path_util(self,dir_s,file_list):
    """Make full path to file"""
    if len(file_list) == 0:
        #skip if new folder with no contents
        logging.info("Probably new directory")
        return
    for file_s in file_list:
        #loop through the files in the dir_s and make a fullpath
        file_path = self.path_join(dir_s,file_s)
        mtime = os.stat(file_path).st_mtime
        if self.mtimes[file_s]["mtime"] == mtime:
            logging.info("No change in mtime")
            return
        self.mtimes[file_s]["path"] = file_path
        self.mtimes[file_s]["mtime"] = mtime
    
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
        for event in self.inotify.read():
            logging.info(f"{event.name},{flags.from_mask(event.mask)}")
            if event.mask & flags.CLOSE_WRITE:
                    logging.info(f"Change detected")
                    
                
            elif event.mask & flags.CREATE and event.mask & flags.ISDIR:
                logging.info(f"New dir detected:{event.name}\n Adding Tracker")
                self.add_tracker()
                
                
if  __name__ == "__main__":
    fileflux = FileFlux(os.getcwd())
    
    fileflux.start_watcher()
                    