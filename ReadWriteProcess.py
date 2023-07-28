##########################################################################
#                                                                        #
#                            ReadWriteProcess                            #
#                                     ~ Process memory manipulator       #
#                                                                        #
#  Copyright (c) 2022, Zackery .R. Smith <zackery.smith82307@gmail.com>. #
#                                                                        #
#  This program is free software: you can redistribute it and/or modify  #
#  it under the terms of the GNU General Public License as published by  #
#  the Free Software Foundation, either version 3 of the License, or     #
#  (at your option) any later version.                                   #
#                                                                        #
#  This program is distributed in the hope that it will be useful,       #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of        #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         #
#  GNU General Public License for more details.                          #
#                                                                        #
#  You should have received a copy of the GNU General Public License     #
#  along with this program. If not, see <http://www.gnu.org/licenses/>.  #
#                                                                        #
##########################################################################
# Curated for LOZUtils, though ReadWriteProcess will work on any process #
##########################################################################

# ; As this was created for LOZUtils (a Legend of Zelda modding utility)
# ; it may not have a feature you are specificly looking for.
# ;
# ; I'm pretty sure ReadWriteProcess will suit the needs of many.
# ; the only thing ReadWriteProcess is really lacking is pointers
# ;
# ; If this project gets 5 stars on github I will add pointers!

# ! This project has some code from ReadWriteMemory. Huge thanks to
# ! Victor M Santiago for making ReadWriteMemory.
# !
# ! Without ReadWriteMemory Windows support on ReadWriteProcess wouldn't
# ! be a thing. https://pypi.org/project/ReadWriteMemory/


#TODO:
#    Create error handling
#    Add custom error messages
#    CLOSE HANDLES IN WINDOWS!
from os import listdir, name
os = name
if os == "nt":
    from os import path
    import ctypes
    import ctypes.wintypes

    # Process Permissions
    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_VM_OPERATION = 0x0008
    PROCESS_VM_READ = 0x0010
    PROCESS_VM_WRITE = 0x0020
    PROCESS_ALL_ACCESS = 0x1f0fff

    MAX_PATH = 260


class Process(object):
    """
    Holds information about the requested process
    """

    def __init__(self, pid:int=-1):
        if os == "nt":
            self.pid = pid
            self.handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, False, pid)

            # Obtain processes name
            if self.handle:
                image_file_name = (ctypes.c_char * MAX_PATH)()
                if ctypes.windll.psapi.GetProcessImageFileNameA(self.handle, image_file_name, MAX_PATH) > 0:
                    filename = path.basename(image_file_name.value)
                    self.name = filename.decode('utf-8')
                else:
                    print(f'Unable to get the executable\'s name for PID={self.process.pid}!')
                    # raise ReadWriteMemoryError(f'Unable to get the executable\'s name for PID={self.process.pid}!')
            else:
                print(f'Process "{self.pid}" not found!')
                # raise ReadWriteMemoryError(f'Process "{self.process.pid}" not found!')

        else:
            self.pid  = pid
            self.name = open(f"/proc/{pid}/comm", "r").read().strip("\n")

    def __repr__(self) -> str: return f'{self.__class__.__name__}: "{self.name}"'

    def open(self):
        """ Open file descriptor (or handle) for the process """
        if os == "nt":
            dw_desired_access = (PROCESS_QUERY_INFORMATION | PROCESS_VM_OPERATION | PROCESS_VM_READ | PROCESS_VM_WRITE)
            b_inherit_handle = True
            self.handle = ctypes.windll.kernel32.OpenProcess(dw_desired_access, b_inherit_handle, self.pid)
            if not self.handle:
                print(f"Unable to open process <{self.name}>")
                #raise ReadWriteMemoryError(f'Unable to open process <{self.name}>')
        else:
            self.fd = open(f"/proc/{self.pid}/mem", "r+b")


    def close(self):
        """ Close file descriptor of the process """
        if os == "nt" : ctypes.windll.kernel32.CloseHandle(self.handle)
        else          : self.fd.close()


    def read(self, addr:int=0x00):
        """ Read data from the process's memory at a specific address 

        Ignores byte size, for reading a specfic byte size use read_byte
        """
        if addr == 0x00 : raise ValueError("Enter a address!")
        
        if os == "nt":
            if addr == 0x00 : raise ValueError("Enter a address!")
            try:
                read_buffer = ctypes.c_uint()
                buffer = ctypes.byref(read_buffer)
                n_size = ctypes.sizeof(read_buffer)
                number_of_bytes_read = ctypes.c_ulong(0)
                ctypes.windll.kernel32.ReadProcessMemory(self.handle, ctypes.c_void_p(addr), buffer,
                                                     n_size, number_of_bytes_read)
                return read_buffer.value
            except (BufferError, ValueError, TypeError) as error:
                if self.handle: self.close()
                error = {'msg': str(error), 'Handle': self.handle, 'PID': self.pid,
                         'Name': self.name}
                print(error)
                #ReadWriteMemoryError(error)
        else:
     
            self.fd.seek(addr)
            value = self.fd.read()
            return int.from_bytes(value, byteorder="little")


    def readByte(self, addr:int=0x00, size:int=1):
        """ Read data from the process's memory at a specific address
        
        Will not read anything over a specified byte size. For adaptive reading use read
        """
        if   addr == 0x00 : raise ValueError("Enter a address!")
        elif size <  0    : raise ValueError("Invalid size! (cannot be negitive)")

        if os == "nt":
            try:
                read_buffer = ctypes.c_ubyte()
                buffer = ctypes.byref(read_buffer)
                n_size = ctypes.sizeof(read_buffer)
                number_of_bytes_read = ctypes.c_ulong(0)
                return [hex(read_buffer.value) for x in range(size) if ctypes.windll.kernel32.ReadProcessMemory(self.handle, ctypes.c_void_p(addr + x), buffer, n_size, number_of_bytes_read)]
            
            except (BufferError, ValueError, TypeError) as error:
                if self.handle: self.close()
                error = {'msg': str(error), 'Handle': self.handle, 'PID': self.pid,
                         'Name': self.name}
                print(error)
                #ReadWriteMemoryError(error)
        else:
        
            self.fd.seek(addr)
            value = self.fd.read(size)
            return int.from_bytes(value, byteorder="little")


    def writeString(self, addr:int=0x00, string:str=None):
        """ Write a string to a address in the process memory
        
        If you are trying to set a specific offset value use write_offset
        """
        if os == "nt":
            try:
                write_buffer = ctypes.create_string_buffer(string.encode())
                buffer = ctypes.byref(write_buffer)
                n_size = ctypes.sizeof(write_buffer)
                number_of_bytes_written = ctypes.c_size_t()
                ctypes.windll.kernel32.WriteProcessMemory(self.handle, addr, buffer,
                                                        n_size, number_of_bytes_written)
                return True
            except (BufferError, ValueError, TypeError) as error:
                if self.handle: self.close()
                error = {'msg': str(error), 'Handle': self.handle, 'PID': self.pid,
                         'Name': self.name}
                print(error)
                #ReadWriteMemoryError(error)
        else:
            if   addr   == 0x00 : raise ValueError("Enter a address!")
            elif string == None : raise ValueError("Enter a string!")
        
            self.fd.seek(addr)
            self.fd.write(string.encode())
            self.fd.flush()


    def writeByte(self, addr:int=0x00, offset:int=0, size:int=-1, value=-1):
        """ Write a value to a specific byte 
        
        Returns true if operation was successful
        """
        if   addr   == 0x00 : raise ValueError("Enter a address!")
        elif size   == -1   : raise ValueError("Enter a byte size!")
        elif value  == -1   : raise ValueError("Enter a value!")
        
        if os == "nt":
            try:
                write_buffer = ctypes.c_uint(value)
                buffer = ctypes.byref(write_buffer)
                number_of_bytes_written = ctypes.c_ulong(0)
                ctypes.windll.kernel32.WriteProcessMemory(self.handle, addr+offset, buffer,
                                                          size, number_of_bytes_written)
                return True
            except (BufferError, ValueError, TypeError) as error:
                if self.handle: self.close()
                error = {'msg': str(error), 'Handle': self.handle, 'PID': self.pid,
                         'Name': self.name}
                print(error)
                #ReadWriteMemoryError(error)
        else:
            self.fd.seek(addr+offset)
            self.fd.write((value).to_bytes(size, "big"))
            self.fd.flush()

            return True

def getRunningProcessesPID() -> list:
    """ Returns a list of all running processes 
    
    The list is just a bunch of PID's if you want the names of the processes
    use getRunningProcessesName
    """
    if os == "nt":
        count = 32
        while True:
            process_ids = (ctypes.wintypes.DWORD * count)()
            cb = ctypes.sizeof(process_ids)
            bytes_returned = ctypes.wintypes.DWORD()
            if ctypes.windll.Psapi.EnumProcesses(ctypes.byref(process_ids), cb, ctypes.byref(bytes_returned)):
                if bytes_returned.value < cb : return list(set(process_ids))
                else                         : count *= 2
    else: 
        return [pid for pid in listdir('/proc') if pid.isdigit()]


def getRunningProcessesName() -> list:
    """ Returns a list of all running processes by name """
    if os == "nt":
        pids = getRunningProcessesPID()
        
        name_pids = []

        for pid in pids:
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, False, pid)
            if handle:
                image_file_name = (ctypes.c_char * MAX_PATH)()
                if ctypes.windll.psapi.GetProcessImageFileNameA(handle, image_file_name, MAX_PATH) > 0:
                    filename = path.basename(image_file_name.value)
                    name_pids.append(filename.decode('utf-8'))
                else:
                    print(f"Unable to get an executable's name for PID={pid}")
                    #raise ReadWriteMemoryError(f'Unable to get the executable\'s name for PID={self.process.pid}!')
            ctypes.windll.kernel32.CloseHandle(handle)
        
        return name_pids
    else:
        return [open(f"/proc/{pid}/comm").read().strip("\n") for pid in listdir('/proc') if pid.isdigit()]

def nameToPID(name:str) -> int:
    if os == "nt":
        if not name.endswith(".exe"): name += ".exe"

        pids = getRunningProcessesPID()

        for pid in pids:
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, False, pid)
            if handle:
                image_file_name = (ctypes.c_char * MAX_PATH)()
                if ctypes.windll.psapi.GetProcessImageFileNameA(handle, image_file_name, MAX_PATH) > 0:
                    filename = path.basename(image_file_name.value)
                    if filename.decode('utf-8') == name: 
                        return pid
            ctypes.windll.kernel32.CloseHandle(handle)

        raise ValueError(f"<{name}> is not a valid process!")
        #raise ReadWriteMemoryError(f'Process "{self.process.name}" not found!')
    else:
        # Try to keep compatibilty
        if name.endswith(".exe"): name = name.strip(".exe")

        pids = getRunningProcessesPID()
        for pid in pids:
            tmp = open(f"/proc/{pid}/comm").read().strip("\n")
            if tmp == name:
                return pid
        raise ValueError(f"<{name}> is not a valid process!")
