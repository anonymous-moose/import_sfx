import sys, json, shutil, os, aifc, math, re, datetime
from os import walk




#notes to self

# get rid of the unused duplicate sounds
# check if the .aiff file is valid, reject it and say what's wrong if it isn't (and which audacity to use)
# do a sanity check before writing, for new samples, that there won't be a name conflict. Cancel the import and raise an error if so
# rigourously make sure that the values set with flags are all valid and won't fuck up the build
# make the import flags actually work
# Throw an error if you try to import a sample into a bank that's already got the maximum amount of instruments
# Borrow Arthur's code for adding loop points?
# Add the ability to create custom instrument banks?
# walk through the sound banks before importing to populate the bankNames dictionary
# implement remove mode
# handle arguments more generally


# arguments:
# mode: "help", or "import"
# decomp directory path
# sound file path
# audio flags


# use this for channel selection

# seq_startchannel 0, .channel0
# seq_startchannel 1, .channel1
# seq_startchannel 2, .channel2
# seq_startchannel 3, .channel38
# seq_startchannel 4, .channel4
# seq_startchannel 5, .channel59
# seq_startchannel 6, .channel6
# seq_startchannel 7, .channel7
# seq_startchannel 8, .channel38
# seq_startchannel 9, .channel59

modes = {
    "import" : ["Imports a sample, or overwrites a previously imported sample.", "[Path to decomp directory] [aiff file to import] (flags)"],
    "remove" : ["Completely removes an imported sample.", "[Path to decomp directory], [aiff file to remove]"],
    "info" : ["Prints info about your sound banks.", "[Path to decomp directory]"],
    "help" : ["Prints this help text on how to use this program.", ""],
}

audioFlags = {
    "-noVolLoss" : ["SOUND_NO_VOLUME_LOSS", "No volume loss with distance."],
    "-vibrato" : ["SOUND_VIBRATO", "Randomly alter frequency each audio frame."],
    "-noPriLoss" : ["SOUND_NO_PRIORITY_LOSS", "Do not prioritize closer sounds."],
    "-constFreq": ["SOUND_CONSTANT_FREQUENCY", "Frequency is not affected by distance or speed. If not set, frequency will increase with distance."],
    "-lowerBGM" : ["SOUND_LOWER_BACKGROUND_MUSIC", "Lower volume of background music while playing."],
    "-noEcho" : ["SOUND_NO_ECHO", "Disable level reverb. Not in JP."],
    "-discrete" : ["SOUND_DISCRETE", "Every call to play_sound restarts the sound. If not set, the sound is continuous and play_sound should be called at least every other frame to keep it playing."]
}

importFlags = {
    "-bank" : ["Choose which sound bank to import the sound into. Default: 0x05."],
    "-priority" : ["The sound priority, an integer from 0 to 255. Higher priority samples will play over lower priority samples. Default: 127"],
    "-channel" : ["Choose which channel to import. Default: "],
    "-version" : ["Whether to import for US or JP. Default: US"],
    "-custom" : ["Whether to add \"custom\" to the imported filename. (Avoids naming conflicts and prevents git from ignoring samples.) Default: 1."],
    "-volume" : ["Sets the volume the sound will play at. Default: 127. Range: (0, 255)"],
    "-velocity" : ["Sets the pitch the sound will play at. Default 39. Range (0, 255)"]
}


# list of banks in order, and their names. 
# For refresh 13, anyways. Shit.
bankNames = {}

newSoundBankJSON = ''
newSoundPlayerFile = ''
newSoundsHeaderFile = ''

# Checks if the "samples" directory even exists. 
def isDecompUsable(decompDir):
    if not os.path.isdir(os.path.join(decompDir, 'sound/samples')):
        print("Error: cannot locate 'samples' directory. Check that you have entered the correct decomp path and have run 'make' at least once.")
        return False
    
    # add more checks here, if needed (decomp too old, ... no write permissions?)

    return True

# sorts a list by the hex byte it starts with. 
def hexByteSort(n):
    return int(n[0:2], 16)



# Does a walk through the sound_banks directory to be sure the bank names are all correct and to account for any custom ones.
def populateBankNames(decompDir):
    bankDir = os.path.join(decompDir, 'sound/sound_banks/')

    (_, _, filenames) = next(os.walk(bankDir))
    filenames.sort(key = hexByteSort)

    for filename in filenames:
        bankNum = str(int(filename[0:2], 16))
        
        
        f = open(os.path.join(decompDir, 'sound/sound_banks/', filename), "r")
        y = json.loads(f.read())
        f.close()

        
        # why the fuck are there ifdefs in the json?!
        bankNames[bankNum] = [filename[:len(filename)-5], y["sample_bank"]["else"] if (type(y["sample_bank"]) == dict) else y["sample_bank"]]
        



def printInfoText(decompDir):
    if(not isDecompUsable(decompDir)):
        return
    populateBankNames(decompDir)
    
    # print out the banks in a nice and tidy manner
    for bank in bankNames.keys():
        print(("\t" + bank.zfill(2) + ": \"" + bankNames[bank][0] + "\" ").ljust(30) + bankNames[bank][1] ) #number, name, sample bank
    



def removeAiff(decompDir, soundFile):
    if(not isDecompUsable(decompDir)):
        return
    print("sorry, not implemented yet")
    return


# prints the help text explaining how to use the tool, and what the various flags do
def printHelpText():
    print("Decomp SFX importer tool for SM64 decomp, by anonymous_moose\n")

    print("\nMODES:")
    for flag in modes.keys():
        print("\t" + flag + "\n\t\t" + modes[flag][0] + "\n\t\t" + "Usage:\timport_sfx.py " + flag + " " + modes[flag][1])

    print("\nAUDIO FLAGS:")
    for flag in audioFlags.keys():
        print("\t" + flag + "\n\t\t" + audioFlags[flag][1])
    
    print("\nIMPORT FLAGS:")
    for flag in importFlags.keys():
        print("\t" + flag + "\n\t\t" + importFlags[flag][0])
    

def checkRange(min, max, n, default):
    if n < min:
        print("Value " + str(n) + " is too small, defaulting to " + str(default))
        return default
    elif n > max:
        print("Value " + str(n) + " is too large, defaulting to " + str(default))
        return default
    return n

def cleanParameter(inputString, min, max, default):
    if inputString.isnumeric():
        return checkRange(min, max, int(inputString), default)
    elif inputString.lower().startswith("0x"):
        try:
            return checkRange(min, max, int(inputString, 16), default)
        except:
            pass
    return default


# imports a new aiff file
def importNewAiff(decompDir, soundFile, cmdFlags):
    print("Importing sound...")
    if(not isDecompUsable(decompDir)):
        return


    populateBankNames(decompDir)

    bankNum = 5
    version = "US"
    soundPriority = 128
    channel = 8 # I dunno. figure this out later
    customName = 1

    # Parse arguments
    # soundFile = sys.argv[2]
    soundName = os.path.splitext(os.path.split(soundFile)[1])

    definedName = ("SOUND_" + soundName[0]).upper()

    # cmdFlags = sys.argv[3:]

    soundFlags = "0"

    overwrite = False #Is the user overwriting an existing sample, or importing a brand new one?

    newSoundBankJSON = ''
    newSoundPlayerFile = ''
    newSoundsHeaderFile = ''


    for i in range(len(cmdFlags)):
        if cmdFlags[i] in audioFlags.keys():
            soundFlags = soundFlags + " | " + audioFlags[cmdFlags[i]][0]
        elif cmdFlags[i] in importFlags.keys():
            if(cmdFlags[i] == "-bank"):
                temp = cleanParameter(cmdFlags[i+1], 0, 255, 5)
                if str(temp) in bankNames.keys():
                    bankNum = temp
                else:
                    print("Bank \"" + str(temp) + "\" does not exist.")
                    #TODO: creating new instrument banks
            elif(cmdFlags[i] == "-priority"):
                soundPriority = cleanParameter(cmdFlags[i+1], 0, 255, 127)
            elif(cmdFlags[i] == "-version") :
                if (cmdFlags[i+1].upper() == "US") or (cmdFlags[i+1].upper() == "JP"):
                    version = cmdFlags[i+1].upper()
                else:
                    print(cmdFlags[i+1] + " is not a recognized version.")
            elif(cmdFlags[i] == "-channel") :
                channel = int(cmdFlags[i+1])
            elif(cmdFlags[i] == "-custom") : #TODO: This is stupid
                customName = int(cmdFlags[i+1])
                soundName[0] = "custom_" + soundName[0]
            else:
                print("yeah i didnt implement that yet sorry")
            i = i + 1


    #calculate length of the sound in seconds.
    a = aifc.open(soundFile, "r")
    
    frames = a.getnframes()
    framerate = a.getframerate()

    print("Sound length is " + str(frames/framerate) + " seconds...")
    
    a.close()
    


    # newFileName = os.path.join(decompDir, 'sound/samples/sfx_5', soundName[0] + soundName[1])

    bankName = bankNames[str(bankNum)][1]
    newFileName = os.path.join(decompDir, 'sound/samples', bankName, soundName[0] + soundName[1])

    if os.path.isfile(newFileName):
        if(input("A file by this name already exists in directory " + "sound/samples/" + bankName + ". Overwrite? [y/N]").lower() == 'y'):
            # If y is chosen, then the file will be renamed
            # shutil.copyfile(soundFile, os.path.join(decompDir, 'sound/samples', bankName, os.path.split(soundFile)[1]))
            overwrite = True
            # print('.aiff file \"' + soundName[0] + soundName[1] + '\" overwritten in \"sound/samples/' + bankName + '\"...')
        else:
            print("Cancelling import.")
            return
    # else:
        # shutil.copyfile(soundFile, os.path.join(decompDir, 'sound/samples', bankName, os.path.split(soundFile)[1]))
        # print('.aiff file \"' + soundName[0] + soundName[1] + '\" copied to \"sound/samples/' + bankName + '\"...')
    

    



    # if we're overwriting an existing sample, don't add a duplicate instrument
    if not overwrite:
        # add to the json
        # try:
        f = open(os.path.join(decompDir, 'sound/sound_banks/' + bankNames[str(bankNum)][0] + '.json'), "r")
        y = json.loads(f.read())
        f.close()

        instNum = str((len(y["instrument_list"])))
        newInst = "inst" + instNum

        y["instrument_list"].append(newInst)

        y["instruments"][newInst] = {
                    "release_rate": 208,
                    "envelope": "envelope0",
                    "sound": soundName[0]
                }

        # Store the current date in the date field. Why not?
        y["date"] = datetime.date.today()

        # Save the contents of the file to write at the end.
        newSoundBankJSON = json.dumps(y, indent=4)

        print("Sound added to bank " + str(bankNum) + "...")
        # except IOError, strerror:
            # print("Cancelling import. Error reading sound bank JSON file: " + strerror)
            # return
    


    # don't add new entries to 00_sound_player.s for overwrites. 
    # if not overwrite:
    #add a sound_ref
    f = open(os.path.join(decompDir, 'sound/sequences/00_sound_player.s'), "r")
    
    if not overwrite:
        # Finds the right channel table to add the sample to, and counts the existing entries to get the index of our new sample.
        completeStage = 0
        bankIndex = 0
        shouldCount = True

        for line in f:
            if completeStage == 0:
                newSoundPlayerFile = newSoundPlayerFile + line
                if '.channel38_table:' in line:
                    completeStage = 1
            elif completeStage == 1:
                if "sound_ref" in line and shouldCount:
                    bankIndex = bankIndex + 1
                elif ".ifdef VERSION_JP" in line:
                    shouldCount = False
                elif not shouldCount and ".else" in line:
                    shouldCount = True
                if line == "\n":
                    newSoundPlayerFile = newSoundPlayerFile + "sound_ref .sound_" + soundName[0] + "\n\n"
                    completeStage = 2
                else:
                    newSoundPlayerFile = newSoundPlayerFile + line
            elif completeStage == 2:
                newSoundPlayerFile = newSoundPlayerFile + line

        
        # Create the asm macro definition for the note.
        #   From my testing, the arguments are the pitch, the duration, and the volume.
        #   Duration is calculated as follows: length in seconds * 48 * 60 * 1/2
        #   The duration is measured in ticks, there are 48 ticks in a beat, 
        #   and the sound effects player has a tempo of 120 beats per minute == 2 beats per second.
        newSoundPlayerFile = (newSoundPlayerFile + "\n.sound_" + soundName[0] + ":\nchan_setbank " + str(bankNum) + "\nchan_setinstr " + str(instNum) + "\nchan_setlayer 0, .layer_" + soundName[0] + "\nchan_end\n\n.layer_" + soundName[0] + ":\nlayer_note1_long 39, " + str(math.ceil((frames/framerate)*1440)) + ", 127\nlayer_end\n")
            
        print("bankIndex = " + str(bankIndex))
    else:
        # for overwrites, we just need to update the play note command, nothing else here.
        completeStage = 0
        for line in f:
            if completeStage == 1:
                newSoundPlayerFile = (newSoundPlayerFile + "layer_note1_long 39, " + str(math.ceil((frames/framerate)*1440)) + ", 127")                
                completeStage = 2
            elif ".layer_" + soundName[0] + ":" in line:
                newSoundPlayerFile = newSoundPlayerFile + line
                completeStage = 1
            else:
                newSoundPlayerFile = newSoundPlayerFile + line




    f.close()
    # print(newSoundPlayerFile)

    

    print("sound_ref created...")
    # else:
        #find the .layer_whatever label corresponding to this sound, 
        #and update the note with volume, pitch, and whatever based on arguments.
        #nothing else needs to be changed or added, here.
        
    
    f = open(os.path.join(decompDir, 'include/sounds.h'), "r")

    if not overwrite:
        for line in f:
            if "#define " + definedName + " " in line:
                print("Cancelling import: A sound with the name \"" + definedName + "\" already exists in a different bank. Please choose a different name.")
                return
            if '#endif // SOUNDS_H' in line:
                newSoundsHeaderFile = newSoundsHeaderFile + ("#define " + definedName).ljust(66) + "SOUND_ARG_LOAD(SOUND_BANK_GENERAL,".ljust(36) + hex(bankIndex) +", " + hex(soundPriority) + ", " + soundFlags + ")\n\n"
            newSoundsHeaderFile = newSoundsHeaderFile + line
    else:
        completeStage = 0
        for line in f:
            if completeStage == 1:
                # For overwrites, only the soundflags are gonna change.
                newSoundsHeaderFile = newSoundsHeaderFile + (re.sub("(,[^,]+\))", ", " + soundFlags + ")", line))
                completeStage = 2
            elif "#define " + definedName + " " in line:
                newSoundsHeaderFile = newSoundsHeaderFile + line
                completeStage = 1
            else:
                newSoundsHeaderFile = newSoundsHeaderFile + line

    f.close()

    print("Sound definition created...")


    # Write all the file changes at the end, in case something errors, the import won't be left half-finished

    # For new imports, each file is changed.
    # For overwriting, an existing sample is updated. 

    # copy the aiff file over
    shutil.copyfile(soundFile, os.path.join(decompDir, 'sound/samples', bankName, os.path.split(soundFile)[1]))

    # Write sound bank json file, if a new sample is being added.
    if not overwrite:
        f = open(os.path.join(decompDir, 'sound/sound_banks/' + bankNames[str(bankNum)][0] + '.json'), "w")
        f.write(newSoundBankJSON)
        f.close()

    # Write the sound player sequence file
    f = open(os.path.join(decompDir, 'sound/sequences/00_sound_player.s'), "w")
    f.write(newSoundPlayerFile)
    f.close()

    # Write the new sound header file
    f = open(os.path.join(decompDir, 'include/sounds.h'), "w")
    f.write(newSoundsHeaderFile)
    f.close()


    print("Import complete! The sound is defined as \"" + definedName + "\".")




#base decomp dir
# decompDir = sys.argv[1]





programMode = sys.argv[1].lower()


if programMode == "import":
    importNewAiff(sys.argv[2], sys.argv[3], sys.argv[4:])
elif programMode == "remove":
    removeAiff(sys.argv[2], sys.argv[3])
elif programMode == "info":
    printInfoText(sys.argv[2])
elif programMode == "help":
    printHelpText()