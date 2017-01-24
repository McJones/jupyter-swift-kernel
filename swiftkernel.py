# coding: utf-8

# a swift kernel for Jupyter
# copyright Tim Nugent, made available under the MIT License
# see the repository https://github.com/McJones/jupyter-swift-kernel/ for full details

import subprocess, os, shutil, tempfile, re
from ipykernel.kernelbase import Kernel

class SwiftKernel(Kernel):
    # Jupiter stuff
    implementation = 'Swift'
    implementation_version = '1.0.1'
    language = 'swift'
    language_version = '3.0.2'
    language_info = {'mimetype': 'text/plain', 'file_extension': 'swift', 'name': 'swift'}
    banner = "Swift kernel"
    # my stuff
    output = []
    swiftDirectory = tempfile.mkdtemp()
    
    def do_execute(self, code, silent, store_history=True, user_expressions=None, allow_stdin=False):
        errorCode, dump = self.runCode(code)
        
        if errorCode == 0:
            # quick and dirty hack to turn utf into ascii
            # need to work out how to get Jupiter to speak utf-8
            a = '\n'.join(dump)
            b = a.decode("utf-8")
            c = b.encode("ascii", "ignore")
            dump = c
            
            if not silent:
                stream = {'name':'stdout', 'text':dump}
                self.send_response(self.iopub_socket, 'stream', stream)
        else:
            # temporary until I can work out the proper error messaging in Jupiter
            stream = {'name':'stdout', 'text':dump}
            self.send_response(self.iopub_socket, 'stream', stream)
        
        return {'status':'ok',
                'execution_count':self.execution_count,
                'payload':[],
                'user_expressions':{}}

    def do_shutdown(self, restart):
        # delete the temporary swift file(s) and directory
        shutil.rmtree(self.swiftDirectory)

    # appends the new text to the swift file
    # runs the swift file
    # capture all output
    # returns the result
    def runCode(self, command):
        swiftFileLocation = os.path.join(self.swiftDirectory, 'scratch.swift')
        canonicalFile = os.path.join(self.swiftDirectory, 'canonical.swift')
        
        # now copy everything from canonical into the scratch
        if os.path.isfile(canonicalFile):
            shutil.copyfile(canonicalFile, swiftFileLocation)
        
        with open(swiftFileLocation, 'a') as swiftFile:
            swiftFile.write("{0}\n".format(command))
            
        newOutput = []
        errorOutput = []
        
        # because who needs warnings, right?!
        # queue up mental picture of Holtzman while reading the above comment please
        cmd = 'swift -suppress-warnings {0}'.format(swiftFileLocation)
        swift = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # handle all valid output
        for line in swift.stdout.readlines():
            newOutput.append(line.rstrip("\n\r"))
        
        # handle any errors
        for line in swift.stderr.readlines():
            # to clean up the default error message swift returns
            line = re.sub('^.*error: ', '', line)
            errorOutput.append(line)
        
        retval = swift.wait()
        
        # ran without error
        if retval == 0:
            # putting the valid code back into the canonical file
            shutil.copyfile(swiftFileLocation, canonicalFile)
            # returning the result
            diff = [x for x in newOutput if x not in self.output]
            self.output = self.output + diff
            return 0, diff
        else:
            # dumping the dodgy file
            os.remove(swiftFileLocation)
            # returning the error(s)
            errorOutput = "".join(errorOutput)
            return 1, errorOutput

if __name__ == '__main__':
    from ipykernel.kernelapp import IPKernelApp
    IPKernelApp.launch_instance(kernel_class=SwiftKernel)
