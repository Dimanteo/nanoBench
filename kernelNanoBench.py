import atexit
import collections
import subprocess
import sys
import os

USING_ADB = False
REMOTEDIR = '/data/local/tmp/'
RAMDISK   = '/tmp/ramdisk/'
AARCH64_BIN_PATH = '../../user/libs/arm64-v8a/'

PFC_START_ASM = '.quad 0xE0b513b1C2813F04'
PFC_STOP_ASM = '.quad 0xF0b513b1C2813F04'

def writeFile(fileName, content):
   with open(fileName, 'w') as f:
      f.write(content);

def assemble(code, objFile, asmFile='/tmp/ramdisk/asm.s'):
   try:
      if not USING_ADB:
         code = '.intel_syntax noprefix;' + code + ';1:;.att_syntax prefix\n'
         with open(asmFile, 'w') as f: f.write(code);
         subprocess.check_call(['as', asmFile, '-o', objFile])
      else:
         code = '.arch armv8-a\n' + code + ';1:;\n'
         with open(asmFile, 'w') as f: f.write(code);
         # should add $NDK_DIR/toolchains/aarch64-linux-android-4.9/prebuilt/linux-x86_64/bin to PATH variable
         subprocess.check_call(['aarch64-linux-android-as', asmFile, '-o', objFile])
   except subprocess.CalledProcessError as e:
      sys.stderr.write('Error (assemble): ' + str(e) + '\n')
      sys.stderr.write(code)
      exit(1)


def objcopy(sourceFile, targetFile):
   try:
      if not USING_ADB:
         subprocess.check_call(['objcopy', sourceFile, '-O', 'binary', targetFile])
      else:
         subprocess.check_call(['aarch64-linux-android-objcopy', sourceFile, '-O', 'binary', targetFile])
   except subprocess.CalledProcessError as e:
      sys.stderr.write('Error (objcopy): ' + str(e) + '\n')
      exit(1)


def filecopy(sourceFile, targetFile):
   try:
      subprocess.check_call(['cp', sourceFile, targetFile])
   except subprocess.CalledProcessError as e:
      sys.stderr.write("Error (cp): " + str(e))
      exit(1)


# Returns the size in bytes.
def getR14Size(using_adb):
   if using_adb:
      return 1000 * 1024 * 1024     # placeholder
   if not hasattr(getR14Size, 'r14Size'):
      with open('/sys/nb/r14_size') as f:
         line = f.readline()
         mb = int(line.split()[2])
         getR14Size.r14Size = mb * 1024 * 1024
   return getR14Size.r14Size


def adbPush(local, remote):
   try:
      subprocess.call(['adb', 'push', local, remote])
   except subprocess.CalledProcessError as e:
      sys.stderr.write(str(e.returncode) + ' ADB could not push ' + local + ' to ' + remote + ' ' + '\n')
      raise e


def adbPull(remote, local):
   try:
      subprocess.call(['adb', 'pull', remote, local])
   except subprocess.CalledProcessError as e:
      sys.stderr.write(str(e.returncode) + ' ADB could not pull ' + remote + ' to ' + local + '\n')
      raise e


def adbExec(cmd):
   try:
      output = subprocess.check_output(['adb', 'shell'] + cmd)
      return output
   except subprocess.CalledProcessError as e:
      query = ''
      for s in cmd: query += s + ' '
      sys.stderr.write(' ADB could not execute "' + query + '" ' + e.output + '\n')
      raise e


ramdiskCreated = False
paramDict = dict()

# Assumes that no changes to the corresponding files in /sys/nb/ were made since the last call to setNanoBenchParameters().
# Otherwise, reset() needs to be called first.
def setNanoBenchParameters(config=None, configFile=None, msrConfig=None, msrConfigFile=None, nMeasurements=None, unrollCount=None, loopCount=None,
                           warmUpCount=None, initialWarmUpCount=None, alignmentOffset=0, codeOffset=0, aggregateFunction=None, basicMode=None, noMem=None,
                           verbose=None):      

   if not ramdiskCreated: createRamdisk()

   if config is not None:
      if paramDict.get('config', None) != config:
         configFile = '/tmp/ramdisk/config'
         writeFile(configFile, config)
         paramDict['config'] = config
   if configFile is not None and not USING_ADB:
      writeFile('/sys/nb/config', configFile)

   if msrConfig is not None:
      if paramDict.get('msrConfig', None) != msrConfig:
         msrConfigFile = '/tmp/ramdisk/msr_config'
         writeFile(msrConfigFile, msrConfig)
         paramDict['msrConfig'] = msrConfig
   if msrConfigFile is not None and not USING_ADB:
      writeFile('/sys/nb/msr_config', msrConfigFile)

   if nMeasurements is not None:
      if paramDict.get('nMeasurements', None) != nMeasurements:
         if not USING_ADB:
            writeFile('/sys/nb/n_measurements', str(nMeasurements))
         paramDict['nMeasurements'] = nMeasurements

   if unrollCount is not None:
      if paramDict.get('unrollCount', None) != unrollCount:
         if not USING_ADB:
            writeFile('/sys/nb/unroll_count', str(unrollCount))
         paramDict['unrollCount'] = unrollCount

   if loopCount is not None:
      if paramDict.get('loopCount', None) != loopCount:
         if not USING_ADB:
            writeFile('/sys/nb/loop_count', str(loopCount))
         paramDict['loopCount'] = loopCount

   if warmUpCount is not None:
      if paramDict.get('warmUpCount', None) != warmUpCount:
         if not USING_ADB:
            writeFile('/sys/nb/warm_up', str(warmUpCount))
         paramDict['warmUpCount'] = warmUpCount

   if initialWarmUpCount is not None:
      if paramDict.get('initialWarmUpCount', None) != initialWarmUpCount:
         if not USING_ADB:
            writeFile('/sys/nb/initial_warm_up', str(initialWarmUpCount))
         paramDict['initialWarmUpCount'] = initialWarmUpCount

   if alignmentOffset is not None:
      if paramDict.get('alignmentOffset', None) != alignmentOffset:
         if not USING_ADB:            
            writeFile('/sys/nb/alignment_offset', str(alignmentOffset))
         paramDict['alignmentOffset'] = alignmentOffset

   if codeOffset is not None:
      if paramDict.get('codeOffset', None) != codeOffset:
         if not USING_ADB:
            writeFile('/sys/nb/code_offset', str(codeOffset))
         paramDict['codeOffset'] = codeOffset

   if aggregateFunction is not None:
      if paramDict.get('aggregateFunction', None) != aggregateFunction:
         if not USING_ADB:
            writeFile('/sys/nb/agg', aggregateFunction)
         paramDict['aggregateFunction'] = aggregateFunction

   if basicMode is not None:
      if paramDict.get('basicMode', None) != basicMode:
         if not USING_ADB:
            writeFile('/sys/nb/basic_mode', str(int(basicMode)))
         paramDict['basicMode'] = basicMode

   if noMem is not None:
      if paramDict.get('noMem', None) != noMem:
         if not USING_ADB:
            writeFile('/sys/nb/no_mem', str(int(noMem)))
         paramDict['noMem'] = noMem

   if verbose is not None:
      if paramDict.get('verbose', None) != verbose:
         if not USING_ADB:
            writeFile('/sys/nb/verbose', str(int(verbose)))
         paramDict['verbose'] = verbose


def resetNanoBench(using_adb):
   global USING_ADB
   USING_ADB = using_adb
   if not using_adb:
      with open('/sys/nb/reset') as resetFile: resetFile.read()
   paramDict.clear()


def addToQuery(query, param, option, has_value=False):
   if param in paramDict:
      if has_value:
         query += [option, str(paramDict[param])]
      elif paramDict[param]:
         query += [option]


def adbRunNanoBench(hasCode, hasInit, hasOneTimeInit):
   query = [REMOTEDIR + 'nb']
   adbPush(AARCH64_BIN_PATH + 'nb', REMOTEDIR)
   if hasCode:
      adbPush(RAMDISK + 'code.bin', REMOTEDIR)
      query += ['-code', REMOTEDIR + 'code.bin']
   if hasInit:
      adbPush(RAMDISK + 'init.bin', REMOTEDIR)
      query += ['-code_init', REMOTEDIR + 'init.bin']
   if hasOneTimeInit:
      adbPush(RAMDISK + 'one_time_init.bin', REMOTEDIR)
      query += ['-code_one_time_init', 'one_time_init.bin']
   if paramDict['config'] is not None:
      adbPush(RAMDISK + 'config', REMOTEDIR)
      query += ['-config', REMOTEDIR + 'config']
   
   query += ['-output', REMOTEDIR + 'adbres']
   addToQuery(query, 'nMeasurements', '-n_measurements', True)
   addToQuery(query, 'unrollCount', '-unroll_count', True)
   addToQuery(query, 'loopCount', '-loop_count', True)
   addToQuery(query, 'warmUpCount', '-warm_up_count', True)
   addToQuery(query, 'initialWarmUpCount', '-initial_warm_up_count', True)
   addToQuery(query, 'alignmentOffset', '-alignment_offset', True)
   query += ['-' + paramDict['aggregateFunction']]
   addToQuery(query, 'basicMode', '-basic_mode')
   addToQuery(query, 'noMem', '-no_mem')
   query += ['-cpu', '0']
   addToQuery(query, 'verbose', '-verbose')
   adbExec(query)
   adbPull(REMOTEDIR + 'adbres', RAMDISK)
   adbExec(['rm', '-r', REMOTEDIR + '*'])
   with open(RAMDISK + 'adbres') as resultFile:
      return resultFile.read()


# code, codeObjFile, codeBinFile cannot be specified at the same time (same for init, initObjFile and initBinFile)
def runNanoBench(code='', codeObjFile=None, codeBinFile=None,
                 init='', initObjFile=None, initBinFile=None,
                 oneTimeInit='', oneTimeInitObjFile=None, oneTimeInitBinFile=None):
   if not ramdiskCreated: createRamdisk()
   if not USING_ADB:
      with open('/sys/nb/clear') as clearFile: clearFile.read()

   if code:
      codeObjFile = '/tmp/ramdisk/code.o'
      assemble(code, codeObjFile)
   if codeObjFile is not None:
      objcopy(codeObjFile, '/tmp/ramdisk/code.bin')
      if not USING_ADB:
         writeFile('/sys/nb/code', '/tmp/ramdisk/code.bin')
   elif codeBinFile is not None:
      if not USING_ADB:
         writeFile('/sys/nb/code', codeBinFile)
      else:
         writeFile('/tmp/ramdisk/code.bin', codeBinFile)

   if init:
      initObjFile = '/tmp/ramdisk/init.o'
      assemble(init, initObjFile)
   if initObjFile is not None:
      objcopy(initObjFile, '/tmp/ramdisk/init.bin')
      if not USING_ADB:
         writeFile('/sys/nb/init', '/tmp/ramdisk/init.bin')
   elif initBinFile is not None:
      if not USING_ADB:
         writeFile('/sys/nb/init', initBinFile)
      else:
         writeFile('tmp/ramdisk/init.bin', initBinFile)

   if oneTimeInit:
      oneTimeInitObjFile = '/tmp/ramdisk/one_time_init.o'
      assemble(oneTimeInit, oneTimeInitObjFile)
   if oneTimeInitObjFile is not None:
      objcopy(oneTimeInitObjFile, '/tmp/ramdisk/one_time_init.bin')
      if not USING_ADB:
         writeFile('/sys/nb/one_time_init', '/tmp/ramdisk/one_time_init.bin')
   elif oneTimeInitBinFile is not None:   
      if not USING_ADB:
         writeFile('/sys/nb/one_time_init', oneTimeInitBinFile)
      else:
         writeFile('/tmp/ramdisk/one_time_init.bin')

   output = ''
   if not USING_ADB:
      with open('/proc/nanoBench') as resultFile:
         output = resultFile.read().split('\n')
   else:
      hasCode = bool(code) or bool(codeBinFile) or bool(codeObjFile)
      hasInit = bool(init) or bool(initBinFile) or bool(initObjFile)
      hasOneTimeInit = bool(oneTimeInit) or bool(oneTimeInitBinFile) or bool(oneTimeInitObjFile)
      output = adbRunNanoBench(hasCode=hasCode, hasInit=hasInit, hasOneTimeInit=hasOneTimeInit).split('\n')

   ret = collections.OrderedDict()
   for line in output:
      if not ':' in line: continue
      line_split = line.split(':')
      counter = line_split[0].strip()
      value = float(line_split[1].strip())
      ret[counter] = value
   print(ret)
   return ret


def createRamdisk():
   try:
      subprocess.check_output('mkdir -p /tmp/ramdisk; sudo mount -t tmpfs -o size=100M none /tmp/ramdisk/', shell=True)
      global ramdiskCreated
      ramdiskCreated = True
   except subprocess.CalledProcessError as e:
      sys.stderr.write('Could not create ramdisk ' + e.output + '\n')
      exit(1)

def deleteRamdisk():
   if ramdiskCreated:
      try:
         subprocess.check_output('sudo umount -l /tmp/ramdisk/', shell=True)
      except subprocess.CalledProcessError as e:
         sys.stderr.write('Could not delete ramdisk ' + e.output + '\n')

atexit.register(deleteRamdisk)