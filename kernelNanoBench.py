import atexit
import collections
import subprocess
import sys

import adbNanoBench as ADB

PFC_START_ASM = '.quad 0xE0b513b1C2813F04'
PFC_STOP_ASM = '.quad 0xF0b513b1C2813F04'
USING_ADB = False

def writeFile(fileName, content):
   with open(fileName, 'w') as f:
      f.write(content);

def assemble(code, objFile, asmFile='/tmp/ramdisk/asm.s'):
   try:
      code = '.intel_syntax noprefix;' + code + ';1:;.att_syntax prefix\n'
      with open(asmFile, 'w') as f: f.write(code);
      subprocess.check_call(['as', asmFile, '-o', objFile])
   except subprocess.CalledProcessError as e:
      sys.stderr.write("Error (assemble): " + str(e))
      sys.stderr.write(code)
      exit(1)


def objcopy(sourceFile, targetFile):
   try:
      subprocess.check_call(['objcopy', sourceFile, '-O', 'binary', targetFile])
   except subprocess.CalledProcessError as e:
      sys.stderr.write("Error (objcopy): " + str(e))
      exit(1)


def filecopy(sourceFile, targetFile):
   try:
      subprocess.check_call(['cp', sourceFile, targetFile])
   except subprocess.CalledProcessError as e:
      sys.stderr.write("Error (cp): " + str(e))
      exit(1)


# Returns the size in bytes.
def getR14Size():
   if not hasattr(getR14Size, 'r14Size'):
      with open('/sys/nb/r14_size') as f:
         line = f.readline()
         mb = int(line.split()[2])
         getR14Size.r14Size = mb * 1024 * 1024
   return getR14Size.r14Size


ramdiskCreated = False
paramDict = dict()

# Assumes that no changes to the corresponding files in /sys/nb/ were made since the last call to setNanoBenchParameters().
# Otherwise, reset() needs to be called first.
def setNanoBenchParameters(config=None, configFile=None, msrConfig=None, msrConfigFile=None, nMeasurements=None, unrollCount=None, loopCount=None,
                           warmUpCount=None, initialWarmUpCount=None, alignmentOffset=0, codeOffset=0, aggregateFunction=None, basicMode=None, noMem=None,
                           verbose=None, using_adb=False):
   global USING_ADB
   USING_ADB = using_adb

   if not ramdiskCreated: createRamdisk()

   if config is not None:
      if paramDict.get('config', None) != config:
         configFile = '/tmp/ramdisk/config'
         writeFile(configFile, config)
         paramDict['config'] = config
   if configFile is not None and not using_adb:
      writeFile('/sys/nb/config', configFile)

   if msrConfig is not None:
      if paramDict.get('msrConfig', None) != msrConfig:
         msrConfigFile = '/tmp/ramdisk/msr_config'
         writeFile(msrConfigFile, msrConfig)
         paramDict['msrConfig'] = msrConfig
   if msrConfigFile is not None and not using_adb:
      writeFile('/sys/nb/msr_config', msrConfigFile)

   if nMeasurements is not None:
      if paramDict.get('nMeasurements', None) != nMeasurements:
         if not using_adb:
            writeFile('/sys/nb/n_measurements', str(nMeasurements))
         paramDict['nMeasurements'] = nMeasurements

   if unrollCount is not None:
      if paramDict.get('unrollCount', None) != unrollCount:
         if not using_adb:
            writeFile('/sys/nb/unroll_count', str(unrollCount))
         paramDict['unrollCount'] = unrollCount

   if loopCount is not None:
      if paramDict.get('loopCount', None) != loopCount:
         if not using_adb:
            writeFile('/sys/nb/loop_count', str(loopCount))
         paramDict['loopCount'] = loopCount

   if warmUpCount is not None:
      if paramDict.get('warmUpCount', None) != warmUpCount:
         if not using_adb:
            writeFile('/sys/nb/warm_up', str(warmUpCount))
         paramDict['warmUpCount'] = warmUpCount

   if initialWarmUpCount is not None:
      if paramDict.get('initialWarmUpCount', None) != initialWarmUpCount:
         if not using_adb:
            writeFile('/sys/nb/initial_warm_up', str(initialWarmUpCount))
         paramDict['initialWarmUpCount'] = initialWarmUpCount

   if alignmentOffset is not None:
      if paramDict.get('alignmentOffset', None) != alignmentOffset:
         if not using_adb:            
            writeFile('/sys/nb/alignment_offset', str(alignmentOffset))
         paramDict['alignmentOffset'] = alignmentOffset

   if codeOffset is not None:
      if paramDict.get('codeOffset', None) != codeOffset:
         if not using_adb:
            writeFile('/sys/nb/code_offset', str(codeOffset))
         paramDict['codeOffset'] = codeOffset

   if aggregateFunction is not None:
      if paramDict.get('aggregateFunction', None) != aggregateFunction:
         if not using_adb:
            writeFile('/sys/nb/agg', aggregateFunction)
         paramDict['aggregateFunction'] = aggregateFunction

   if basicMode is not None:
      if paramDict.get('basicMode', None) != basicMode:
         if not using_adb:
            writeFile('/sys/nb/basic_mode', str(int(basicMode)))
         paramDict['basicMode'] = basicMode

   if noMem is not None:
      if paramDict.get('noMem', None) != noMem:
         if not using_adb:
            writeFile('/sys/nb/no_mem', str(int(noMem)))
         paramDict['noMem'] = noMem

   if verbose is not None:
      if paramDict.get('verbose', None) != verbose:
         if not using_adb:
            writeFile('/sys/nb/verbose', str(int(verbose)))
         paramDict['verbose'] = verbose


def resetNanoBench():
   if not USING_ADB:
      with open('/sys/nb/reset') as resetFile: resetFile.read()
   paramDict.clear()


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
      else:
         ADB.push('/tmp/ramdisk/code.bin', ADB.TMPDIR)
   elif codeBinFile is not None:
      if not USING_ADB:
         writeFile('/sys/nb/code', codeBinFile)
      else:
         ADB.push(codeBinFile, ADB.TMPDIR + 'code')

   if init:
      initObjFile = '/tmp/ramdisk/init.o'
      assemble(init, initObjFile)
   if initObjFile is not None:
      objcopy(initObjFile, '/tmp/ramdisk/init.bin')
      if not USING_ADB:
         writeFile('/sys/nb/init', '/tmp/ramdisk/init.bin')
      else:
         ADB.push('/tmp/ramdisk/init.bin', ADB.TMPDIR + 'init')
   elif initBinFile is not None:
      if not USING_ADB:
         writeFile('/sys/nb/init', initBinFile)
      else:
         ADB.push(initBinFile, ADB.TMPDIR + 'init')

   if oneTimeInit:
      oneTimeInitObjFile = '/tmp/ramdisk/one_time_init.o'
      assemble(oneTimeInit, oneTimeInitObjFile)
   if oneTimeInitObjFile is not None:
      objcopy(oneTimeInitObjFile, '/tmp/ramdisk/one_time_init.bin')
      if not USING_ADB:
         writeFile('/sys/nb/one_time_init', '/tmp/ramdisk/one_time_init.bin')
      else:
         ADB.push('/tmp/ramdisk/one_time_init.bin', ADB.TMPDIR + 'one_time_init')
   elif oneTimeInitBinFile is not None:   
      if not USING_ADB:
         writeFile('/sys/nb/one_time_init', oneTimeInitBinFile)
      else:
         ADB.push(oneTimeInitBinFile, ADB.TMPDIR + 'one_time_init')

   output = ''
   if not USING_ADB:
      with open('/proc/nanoBench') as resultFile:
         output = resultFile.read().split('\n')
   else:
      output = ADB.runNanoBench().split('\n')

   ret = collections.OrderedDict()
   for line in output:
      if not ':' in line: continue
      line_split = line.split(':')
      counter = line_split[0].strip()
      value = float(line_split[1].strip())
      ret[counter] = value

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
         subprocess.check_output('umount -l /tmp/ramdisk/', shell=True)
      except subprocess.CalledProcessError as e:
         sys.stderr.write('Could not delete ramdisk ' + e.output + '\n')

atexit.register(deleteRamdisk)