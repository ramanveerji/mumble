#!/usr/bin/env python3
#
# Copyright 2015-2023 The Mumble Developers. All rights reserved.
# Use of this source code is governed by a BSD-style license
# that can be found in the LICENSE file at the root of the
# Mumble source tree or at <https://www.mumble.info/LICENSE>.

from __future__ import (unicode_literals, print_function, division)

import argparse
import os
import platform
import sys
from pathlib import Path

allowed_components = ('qt', 'qtbase')
local_qt_translations = []
override_qt = []

def parseTranslationsConfig(configFile):
    configHandle = open(configFile, "r")

    for currentLine in configHandle:
        currentLine = currentLine.strip()
        # Skip comments and empty lines
        if currentLine.startswith("#") or not currentLine:
            continue

        # A config entry is supposed to be in the format <operator> <fileName>
        splitParts = currentLine.split(" ", 1)
        if len(splitParts) != 2:
            raise RuntimeError(f"Invalid line in translation config file: {currentLine}")

        operator = splitParts[0].lower().strip()
        translationFileName = splitParts[1].strip()

        if not translationFileName:
            raise RuntimeError(f"Empty filename in translation config: {currentLine}")

        if not translationFileName.endswith(".ts"):
            raise RuntimeError(
                f"Expected translation file to have a '*.ts' name but got {translationFileName}"
            )

        # Replace the trailing .ts with .qm as this is what lrelease will turn it into
        translationFileName = f"{translationFileName[:-3]}.qm"

        local_qt_translations.append(translationFileName)

        if operator == "fallback":
            # fallback files are the default, so no special action has to be taken
            pass
        elif operator in ["overwrite", "override"]:
            override_qt.append(translationFileName)


def getComponentName(fileName):
    # Remove file extension
    fileName = os.path.splitext(fileName)[0]

    lastUnderscoreIdx = fileName.rfind('_')
    if lastUnderscoreIdx == -1:
        return ""

    component = fileName[:lastUnderscoreIdx]
    lang = fileName[lastUnderscoreIdx+1:]
    # Handle en_US-style locale names
    if lang.upper() == lang:
        lastUnderscoreIdx = component.rfind('_')
        component = fileName[:lastUnderscoreIdx]
        lang = fileName[lastUnderscoreIdx+1:]

    return component


def dirToQrc(outFile, directoryPath, processedComponents, localTranslationDir = False):
    absPath = os.path.abspath(directoryPath)

    fileNames = os.listdir(absPath)

    return filesToQrc(outFile, processedComponents, fileNames, absPath, localTranslationDir)


def filesToQrc(outFile, processedComponents, fileNames, directoryPath, localTranslationDir = False):
    for currentFileName in fileNames:
        isOverride = False

        if currentFileName in override_qt and localTranslationDir:
            # This translation should be used to overwrite an existing Qt-translation.
            isOverride = True

        name, extension = os.path.splitext(currentFileName)
        if extension != ".qm":
            continue

        component = getComponentName(currentFileName)

        if component not in allowed_components:
            continue

        if name in processedComponents and not isOverride:
            continue

        currentFilePath = os.path.join(directoryPath, currentFileName)
        if not isOverride:
            print("   > Bundling Qt translation \"{0}\"".format(currentFilePath))
            outFile.write(' <file alias="{0}">{1}</file>\n'.format(currentFileName, currentFilePath))
            processedComponents.append(name)
        else:
            # In order to recognize translation-overrides, we have to prefix them
            print("   > Bundling Qt overwrite translation \"{0}\"".format(currentFilePath))
            outFile.write(
                ' <file alias="{0}">{1}</file>\n'.format(
                    f"mumble_overwrite_{currentFileName}", currentFilePath
                )
            )

    return processedComponents



def main():
    # python generate-mumble_qt-qrc.py <output-fn> [inputs...] localDir
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", help="The path to which to write the generated QRC file", metavar="PATH", required=True)
    parser.add_argument("--translation-dir", help="The path to the directory containing the official Qt translations",
            action="append", metavar="PATH", required=True)
    parser.add_argument("--local-translation-dir", help="The path to the local translation directory", metavar="PATH", required=True)

    args = parser.parse_args()

    # parse config file
    configFile = os.path.join(args.local_translation_dir, "translations.conf")
    if os.path.isfile(configFile):
        parseTranslationsConfig(configFile)

    with open(args.output, 'w') as of:
        of.write('<!DOCTYPE RCC><RCC version="1.0">\n')
        of.write('<qresource>\n')
        processedComponents = []
        for dirName in args.translation_dir:
            processedComponents.extend(dirToQrc(of, dirName, processedComponents))
        # Process translations provided by Mumble itself (aka local translations)
        filesToQrc(of, processedComponents, local_qt_translations, args.local_translation_dir, True)
        of.write('</qresource>\n')
        of.write('</RCC>\n')

if __name__ == '__main__':
    main()
