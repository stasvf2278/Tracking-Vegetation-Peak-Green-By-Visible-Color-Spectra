#-------------------------------------------------------------------------------
# Name:        TrackingVegetationPeakGreenByColorSpectra
# Purpose:     Provide average color values (e.g. RGB, vNDVI) for a directory
#              and its subdirectories by date for Climate assessment by photo
#              imagery
#
# Author:      Stanley Mordensky
#
# Created:     1/3/2020
# Copyright:   (c) Stanley Mordensky 2020
# Licence:     CC 3.0
#-------------------------------------------------------------------------------

import time, mplcursors, colorsys, os, os.path, cv2, shutil, PIL

from PIL import Image
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from pandas.plotting import register_matplotlib_converters
from datetime import datetime
from matplotlib import cm

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.dates as mpl_dates


def processImages(filepath, crop_im_path, selected_images, var_list):
    '''Selects, crops, and computes cropped images to numerical values; also copies selected and cropped images to sub directories'''

    ## Added for second recursive file walk
    filepath2 = filepath

    ## Redefine filepath for custom-written recursive walk
    filepath = os.path.abspath(os.path.expanduser(os.path.expandvars(filepath)))

    ## Create dataframe
    df = pd.DataFrame(columns = var_list)

    ## Loops through file directory
    ## Gives depth recusive walk will go; 2 means root directory folder and 1 additional folder
    depth = 2

    ## Create list into which the recursive directory walks write dates from images as they process.
    ## This list is then compared to the dates of remaning images to prevent duplicate analyses (potentially at multiple times) on the same day
    dateList = []

    ## To recursively walk most of the folders
    for root, dirs, files in os.walk(filepath):
        if root[len(filepath):].count(os.sep) < depth:
            ##Starts with 4 pm times (16:00) and then goes down list earlier times if no later times are found
            times = [16, 15, 4]
            for i in range(len(times)):
                for file in files:
                    filename = os.path.join(root, file)
                    if int(time.strftime('%H', time.localtime(os.path.getmtime(filename)))) == times[i]:
                        if int(time.strftime('%M', time.localtime(os.path.getmtime(filename)))) <= 2:
                            if filename.endswith('.JPG'):
                                        ## Calls function to produce color statistics and meta data on -filename-
                                        feature_row = image_to_data(filename, crop_im_path)
                                        ## Checks that the a file from a later time has not already been appended
                                        if feature_row[6] not in dateList:
                                            ## Copy original file to selected_images folder
                                            shutil.copy2(filename, selected_images)
                                            ## Provides output to show script is working
                                            print(feature_row)
                                            ## Adds color statistics and meta data to df
                                            to_append = feature_row
                                            df_length = len(df)
                                            df.loc[df_length] = to_append
                                            ##Append dateList
                                            dateList.append(feature_row[6])

##    ## To recursively walk the folders with unusual time stamps (a.k.a. the problem files)
##    ## Commented out in the absence of folders with unusual time stamps
##    for root, dirs, files in os.walk(filepath2):
##        if root[len(filepath):].count(os.sep) < depth:
##            for dir in dirs:
##                ## Place directories with problem files here
##                if dir in {##}:
##                    complete_dir = os.path.join(root, dir)
##                    # print(complete_dir)
##                    for root2, dirs2, files2 in os.walk(complete_dir):
##                        ##Starts with 4 pm times (16:00) and then goes down list earlier times if no later times are found
##                        times = [16, 17, 15, 14, 13, 12, 11, 10]
##                        for i in range(len(times)):
##                            for file in files2:
##                                filename = os.path.join(root2, file)
##                                ##Append append feature row to xlsx IF the it is the latest file for that date
##                                if int(time.strftime('%H', time.localtime(os.path.getmtime(filename)))) == times[i]:
##                                    if filename.endswith('.JPG'):
##                                        ## Calls function to produce color statistics and meta data on -filename-
##                                        feature_row = image_to_data(filename, crop_im_path)
##                                        ## Checks that the a file from a later time has not already been appended
##                                        if feature_row[6] not in dateList:
##                                            ## Copy original file to selected_images folder
##                                            shutil.copy2(filename, selected_images)
##                                            ## Provides output to show script is working
##                                            print(feature_row)
##                                            ## Adds color statistics and meta data to df
##                                            to_append = feature_row
##                                            df_length = len(df)
##                                            df.loc[df_length] = to_append
##                                            ##Append dateList
##                                            dateList.append(feature_row[6])

    return df


def image_to_data(file, crop_im_path):
    '''Crop and call color spectra functions (extract_color_stats() to then assign the spectra data to an .xlsx sheet)'''

    im = Image.open(file)

    height, width = im.size

    ## Set cropping extent by pixel value
    ## Farthest left pixel
    left = 0
    ## top = width/2 crops out top half of image !!I don't know why width and height are reversed, but this is the way it works!!
    top = width/2
    ## Farthest right pixel
    right = height
    ## Bottom of image
    bottom = width*0.9

    ## Crop function as a part of PIL
    im_crop = im.crop((left, top, right, bottom))

    ## Calls extract_color_stats function on cropped image
    feature_row = extract_color_stats(im_crop)

    ##Gets date and converts to datetime
    date = getDate(file)
    ## Creates timestamp to parse by hour collected
    timestamp = time.strftime('%H:%M:%S', time.localtime(os.path.getmtime(file)))

    ## Adds -date- variable to .xlsx sheet
    feature_row.append(date)
    ## Adds -timestamp- variable to .xlsx sheet
    feature_row.append(timestamp)
    ## ## Adds -filename- variable to .xlsx sheet
    feature_row.append(os.path.basename(file))
    ## Adds YIQ, HLS, HSV systems to row
    feature_row.extend(convert_color_system(feature_row[0], feature_row[1], feature_row[2]))

    ## Save cropped image
    im_crop_filename = crop_im_path + '\\' + 'cropped_' + os.path.basename(file)
    im_crop = im_crop.save(im_crop_filename)

    ## Creates count of contours in cropped image by calling contourCount in len() with im_crop_filename
    conLen = len(contourCount(im_crop_filename))

    ## Appends Contour Length to feature_row list
    feature_row.append(conLen)

    ## Adds VIGreen to row
    feature_row.append(VIGreen(feature_row[0], feature_row[1], feature_row[2]))
    ## Adds VARI to row
    feature_row.append(VARI(feature_row[0], feature_row[1], feature_row[2]))
    ## Adds vNDVI
    feature_row.append(vNDVI(feature_row[0], feature_row[1], feature_row[2]))
    ## Add Hue Degrees
    feature_row.append(hue_degrees(feature_row[0], feature_row[1], feature_row[2]))

    ## Returns feature_row list [] to main()
    return(feature_row)


def extract_color_stats(image):
    '''Identify, average, and return R, G, B average and standarard deviation values for an image'''

    (R, G, B,) = image.split()
    features = [np.mean(R), np.mean(G), np.mean(B), np.std(R), np.std(G), np.std(B)]
    ## Returns features (the color statistics) to image_to_data()
    return features


def getDate(file):
    '''Gets date in datetime format'''

    ## Finds the date modified by Year, Day, Month
    date = time.strftime('%Y/%m/%d', time.localtime(os.path.getmtime(file)))
    ## Turns -date- variable into a datetime !!I'm still looking for a way to remove the 00:00:00 output on the .xlsx sheet!!
    date = datetime.strptime(date, '%Y/%m/%d')

    return date


def convert_color_system(R, G, B):
    '''Convert RGB to YIQ, HLS, and HSV'''

    ## Convert R, G, B from 0 - 255 to 0 to 1.0
    R, G, B = R / 255, G / 255, B / 255

    ## Start new list for YIQ, HLS, and HSV values
    new_color_systems = []

    ## Convert RGB to YIQ and extend new_color_systems[] with YIQ
    new_color_systems.extend(list(colorsys.rgb_to_yiq(R, G, B)))
    ## Convert RGB to HLS and extend new_color_systems[] with HLS
    new_color_systems.extend(list(colorsys.rgb_to_hls(R, G, B)))
    ## Convert RGB to HSV and extend new_color_systems[] with HSV
    new_color_systems.extend(list(colorsys.rgb_to_hsv(R, G, B)))

    ##Returns YIQ, HLS, and HSV values, respectively, as a list
    return new_color_systems


def contourCount(image):
    '''Completes and quantifies edge detection; edge detection values were arbitrary chosen (see https://www.pythonforengineers.com/image-and-video-processing-in-python/)'''

    ## CV2 reads image
    image = cv2.imread(image)

    ## Blur image
    blurred_image = cv2.GaussianBlur(image, (7,7), 0)

    ## Canny operation on image
    canny = cv2.Canny(blurred_image, 10, 30)

    ## Identify the contours in the image
    contours, hierarchy = cv2.findContours(canny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    ## Return contours
    return contours


def VIGreen(R, G, B):
    '''Creates and returns VIGreen from RGB (see Costa et al. 2020; A new visible band index... Computers and Electronics in Agriculture)'''
    VIGreen = (G - R) / (G + R)
    return VIGreen


def VARI(R, G, B):
    '''Creates and returns VARI from RGB (see Costa et al. 2020; A new visible band index... Computers and Electronics in Agriculture)'''
    VARI = (G - R) / (G + R - B)
    return VARI


def vNDVI(R, G, B):
    '''Creates and returns vNDVI from RGB (see Costa et al. 2020; A new visible band index... Computers and Electronics in Agriculture)'''
    vNDVI = 0.5268 * ((R/255)**(-0.1294)) * ((G/255)**(0.3389)) * ((B/255)**(-0.3118))
    return vNDVI


def hue_degrees(R, G, B):
    '''Gives hue on a scale of 0 to 360'''

    ## Convert R, G, B from 0 - 255 to 0 to 1.0
    R, G, B = R / 255, G / 255, B / 255

    ## Produce HSV list
    hsv = colorsys.rgb_to_hsv(R, G, B)
    ## Isolate and multiply H by 360 to get degrees
    hue_deg = hsv[0] * 360
    ## Return Hue in degrees
    return hue_deg


def movingAverage(df, var_list, var_list2):
    '''Create 5-day moving average for RGB, YIQ, HLS, HSV, and contours'''

    ## Convert to datetime
    df[var_list[6]] = pd.to_datetime(df[var_list[6]])

    ## Sort df by date, create new dataframe (df_sorted) with index reset
    # df.sort_values(var_list[6], inplace=True)
    df_sorted = df.sort_values(var_list[6])
    df_sorted = df_sorted.reset_index(drop=True)


    ## RGB 5-day moving average to df
    df_sorted[var_list2[0]] = df_sorted.iloc[:,0].rolling(window=5).mean()
    df_sorted[var_list2[1]] = df_sorted.iloc[:,1].rolling(window=5).mean()
    df_sorted[var_list2[2]] = df_sorted.iloc[:,2].rolling(window=5).mean()

    ## YIQ 5-day moving average to df_sorted
    df_sorted[var_list2[3]] = df_sorted.iloc[:,9].rolling(window=5).mean()
    df_sorted[var_list2[4]] = df_sorted.iloc[:,10].rolling(window=5).mean()
    df_sorted[var_list2[5]] = df_sorted.iloc[:,11].rolling(window=5).mean()

    ## HLS 5-day moving average to df_sorted
    df_sorted[var_list2[6]] = df_sorted.iloc[:,12].rolling(window=5).mean()
    df_sorted[var_list2[7]] = df_sorted.iloc[:,13].rolling(window=5).mean()
    df_sorted[var_list2[8]] = df_sorted.iloc[:,14].rolling(window=5).mean()

    ## HSV 5-day moving average to df_sorted
    df_sorted[var_list2[9]] = df_sorted.iloc[:,15].rolling(window=5).mean()
    df_sorted[var_list2[10]] = df_sorted.iloc[:,16].rolling(window=5).mean()
    df_sorted[var_list2[11]] = df_sorted.iloc[:,17].rolling(window=5).mean()

    ## Contour 5-day moving average to df_sorted
    df_sorted[var_list2[12]] = df_sorted.iloc[:,18].rolling(window=5).mean()

    ## VIgreen 5-day moving average to df_sorted
    df_sorted[var_list2[13]] = df_sorted.iloc[:,19].rolling(window=5).mean()

    ## VARI 5-day moving average to df_sorted
    df_sorted[var_list2[14]] = df_sorted.iloc[:,20].rolling(window=5).mean()

    ## vNDVI 5-day moving average to df_sorted
    df_sorted[var_list2[15]] = df_sorted.iloc[:,21].rolling(window=5).mean()

    return(df_sorted)


def createXLSX(output_dir, output_base, df_sorted):
    '''Exports df to .xlsx file'''

    ## Create and open workbook
    wb = Workbook()
    ws = wb.active

    ## Writes df to .xlsx
    for r in dataframe_to_rows(df_sorted, index=True, header=True):
        ws.append(r)

    ## Saves the workbook
    wb.save(output_dir + '\\' + output_base + '.XLSX')


def RGBPlot_std(output_dir, output_base, var_list, df_sorted):
    '''Create RGB Plot with standard deviation values'''

    ## Setups up 1 x 3 subplot grid
    fig0, axs = plt.subplots(3, 1, sharey = True, sharex = True, figsize = (10, 10))

    ## Adds data frames to subplots, in order of R, G, B
    axs[0].plot(df_sorted[var_list[6]], df_sorted[var_list[0]], marker = 'None', linestyle = 'solid', color = 'red', label='R')
    axs[0].plot(df_sorted[var_list[6]], (df_sorted[var_list[0]]-df_sorted[var_list[3]]), marker = 'None', linestyle = '--', color = 'red', label='R 1 STD')
    axs[0].plot(df_sorted[var_list[6]], (df_sorted[var_list[0]]+df_sorted[var_list[3]]), marker = 'None', linestyle = '--', color = 'red')

    axs[1].plot(df_sorted[var_list[6]], df_sorted[var_list[1]], marker = 'None', linestyle = 'solid', color = 'green', label='G')
    axs[1].plot(df_sorted[var_list[6]], (df_sorted[var_list[1]]-df_sorted[var_list[4]]), marker = 'None', linestyle = '--', color = 'green', label='G 1 STD')
    axs[1].plot(df_sorted[var_list[6]], (df_sorted[var_list[1]]+df_sorted[var_list[4]]), marker = 'None', linestyle = '--', color = 'green')

    axs[2].plot(df_sorted[var_list[6]], df_sorted[var_list[2]], marker = 'None', linestyle = 'solid', color = 'blue', label='B')
    axs[2].plot(df_sorted[var_list[6]], (df_sorted[var_list[2]]-df_sorted[var_list[5]]), marker = 'None', linestyle = '--', color = 'blue', label='B 1 STD')
    axs[2].plot(df_sorted[var_list[6]], (df_sorted[var_list[2]]+df_sorted[var_list[5]]), marker = 'None', linestyle = '--', color = 'blue')

    ## Creates legend, loc sets legend placement
    fig0.legend(loc=(0.815, 0.03))

    ## Change background of plotting area to white
    fig0.patch.set_facecolor('white')

    ## Set sublabels on Y axis
    axs[0].set_ylabel('R')
    axs[1].set_ylabel('G')
    axs[2].set_ylabel('B')

    ## Format dates
    plt.gcf().autofmt_xdate()
    date_format = mpl_dates.DateFormatter('%d %b. %Y')
    plt.gca().xaxis.set_major_formatter(date_format)

    ## Add common title
    fig0.suptitle('RGB Values by Date')

    ## Add common axes
    ## add a big axis, hide frame
    fig0.add_subplot(111, frameon=False)
    ## Hide tick and tick label of the big axis
    plt.tick_params(labelcolor='none', top=False, bottom=False, left=False, right=False)
    plt.style.use('seaborn')
    plt.xlabel('Date', labelpad=35)
    plt.ylabel('Data Value\n(0 - 255)', labelpad=20)

    # ## Identifies data point by data on cursor drag
    cursor = mplcursors.cursor(hover=True)
    cursor.connect("add", lambda sel: sel.annotation.set_text("{}\n{}".format(df_sorted[var_list[8]][sel.target.index],df_sorted[var_list[6]][sel.target.index])))

    ## Create figx to save figx as a file in order to use plt.show() (plt.show() removes the plot automatically after being called)
    ## Saves the figure
    figx0 = plt.gcf()
    figx0.savefig(output_dir + '\\' + output_base + 'RGB_wStandDev.JPG', facecolor=figx0.get_facecolor(), edgecolor = 'none')
    ## Plots interactive figure
    plt.show(block=False)
    plt.pause(0.1)
    plt.close()


def multiPlot(output_dir, output_base, var_list, var_list2, df_sorted):
    '''Creates RGB, YIQ, HSL, HSV, and STD (of RGB) plots'''

    ## Creates a list of lists specific to each plot
    ## Add new plots by adding to this list [Plot 1 values, Plot 2 value, Plot 3 Values, Plot Title]
    plotList = [
        [df_sorted[var_list[0]], df_sorted[var_list[1]], df_sorted[var_list[2]], 'RGB'],
        [df_sorted[var_list[9]], df_sorted[var_list[10]], df_sorted[var_list[11]], 'YIQ'],
        [df_sorted[var_list[12]], df_sorted[var_list[13]], df_sorted[var_list[14]], 'HLS'],
        [df_sorted[var_list[15]], df_sorted[var_list[16]], df_sorted[var_list[17]], 'HSV'],
        [df_sorted[var_list[3]], df_sorted[var_list[4]], df_sorted[var_list[5]], 'RGB Standard Deviation'],
        [df_sorted[var_list2[0]], df_sorted[var_list2[1]], df_sorted[var_list[2]], 'RGB SMA 5'],
        [df_sorted[var_list2[3]], df_sorted[var_list2[4]], df_sorted[var_list2[5]], 'YIQ SMA 5'],
        [df_sorted[var_list2[6]], df_sorted[var_list2[7]], df_sorted[var_list2[8]], 'HLS SMA 5'],
        [df_sorted[var_list2[9]], df_sorted[var_list2[10]], df_sorted[var_list2[11]], 'HSV SMA 5']
    ]

    for i in plotList:

        ## Setups up 1 x 3 subplot grid
        fig, ax2 = plt.subplots(3, 1, sharey = False, sharex = True, figsize = (10, 10))

        ## Adds data frames to subplots, in order of RGB; YIQ; HLS; HSV
        ax2[0].plot(df_sorted[var_list[6]], i[0], marker = 'None', linestyle = 'solid', color = 'red', label=str(i[3][0]))
        ax2[1].plot(df_sorted[var_list[6]], i[1], marker = 'None', linestyle = 'solid', color = 'green', label=str(i[3][1]))
        ax2[2].plot(df_sorted[var_list[6]], i[2], marker = 'None', linestyle = 'solid', color = 'blue', label=str(i[3][2]))

        ## Creates legend, loc sets legend placement
        fig.legend(loc=(0.815, 0.03))



        ## Set sublabels on Y axis
        ax2[0].set_ylabel(str(i[3][0]))
        ax2[1].set_ylabel(str(i[3][1]))
        ax2[2].set_ylabel(str(i[3][2]))

        ## Change background of plotting area to white
        ax2[0].set_facecolor('white')
        ax2[1].set_facecolor('white')
        ax2[2].set_facecolor('white')

        ## Format dates
        plt.gcf().autofmt_xdate()
        date_format = mpl_dates.DateFormatter('%d %b. %Y')
        plt.gca().xaxis.set_major_formatter(date_format)

        ## Add common title
        fig.suptitle(i[3] + ' Values by Date')

        ## Add common axes
        ## add a big axis, hide frame
        fig.add_subplot(111, frameon=False)
        ## Hide tick and tick label of the big axis
        plt.tick_params(labelcolor='none', top=False, bottom=False, left=False, right=False)
        plt.style.use('seaborn')
        plt.xlabel('Date', labelpad=35)
        plt.ylabel('Data Value\n(0 - 255)', labelpad=20)

        # ## Identifies data point by data on cursor drag
        cursor = mplcursors.cursor(hover=True)
        cursor.connect("add", lambda sel: sel.annotation.set_text("{}\n{}".format(df_sorted[var_list[8]][sel.target.index],df_sorted[var_list[6]][sel.target.index])))

        fig.patch.set_facecolor('white')

        ## Create fig1 to save fig1 as a file in order to use plt.show() (plt.show() removes the plot automatically after being called)
        ## Saves the figure
        figx = plt.gcf()
        figx.savefig(output_dir + '\\' + output_base + '_' + str(i[3]) + '.JPG', facecolor=figx.get_facecolor(), edgecolor = 'none')
        ## Plots interactive figure
        plt.show(block=False)
        plt.pause(0.1)
        plt.close()


def singlePlot(output_dir, output_base, var_list, var_list2, df_sorted):
    '''Creates plot of quanitified edges'''

    plotList = [
        [df_sorted[var_list[18]], 'Contour'],
        [df_sorted[var_list[19]], 'VI Green'],
        [df_sorted[var_list[20]], 'VARI'],
        [df_sorted[var_list[21]], 'vNDVI'],
        [df_sorted[var_list[22]], 'Hue Degrees'],
        [df_sorted[var_list2[12]], 'Contour SMA 5'],
        [df_sorted[var_list2[13]], 'VI Green SMA 5'],
        [df_sorted[var_list2[14]], 'VARI SMA 5'],
        [df_sorted[var_list2[15]], 'vNDVI SMA 5']
    ]

    for i in plotList:

        ## Adds data frame to single data plots
        plt.plot(df_sorted[var_list[6]], i[0], marker = 'None', linestyle = 'solid', color = 'black', label='Contour Count')
        plt.xlabel('Date')
        plt.ylabel(i[1])
        plt.title(i[1])

        ax = plt.gca()
        ax.set_facecolor('white')

        ## Format dates
        plt.gcf().autofmt_xdate()
        date_format = mpl_dates.DateFormatter('%d %b. %Y')
        plt.gca().xaxis.set_major_formatter(date_format)

        ## Identifies data point by data on cursor drag
        cursor = mplcursors.cursor(hover=True)
        cursor.connect("add", lambda sel: sel.annotation.set_text("{}\n{}".format(df_sorted[var_list[8]][sel.target.index],df_sorted[var_list[6]][sel.target.index])))


        ## Create figx to save figx as a file in order to use plt.show() (plt.show() removes the plot automatically after being called)
        ## Saves the figure
        figx1 = plt.gcf()
        figx1.savefig(output_dir + '\\' + output_base + i[1] + '.JPG', facecolor=figx1.get_facecolor(), edgecolor = 'none')
        ## Plots interactive figure
        plt.show(block=False)
        plt.pause(0.1)
        plt.close()


def ColorBars(output_dir, output_base, var_list, df_sorted):
    '''Create color bar plot'''

    #Adds a new column with an arbitrary value (100) to produce bar graphs
    df_sorted['Bar Value'] = 100
    df_sorted['R Norm'] = df_sorted[var_list[0]]/255
    df_sorted['G Norm'] = df_sorted[var_list[1]]/255
    df_sorted['B Norm'] = df_sorted[var_list[2]]/255

    rgb = df_sorted[['R Norm', 'G Norm', 'B Norm']]
    tuples = [tuple(x) for x in rgb.to_numpy()]

    # print(tuples)

    ## Adds data frames to subplots, in order of H, S, V
    plt.bar(df_sorted[var_list[6]], df_sorted['Bar Value'], color = tuples)

    ax = plt.gca()
    ax.set_facecolor('white')

    plt.xlabel('Date')
    plt.ylabel('Color by Average RGB Value')
    plt.title('RGB Color Bars by Date')

    plt.tick_params(
    axis='y',          # changes apply to the x-axis
    which='both',      # both major and minor ticks are affected
    left=False,      # ticks along the bottom edge are off
    right=False,         # ticks along the top edge are off
    labelleft=False) # labels along the bottom edge are off

    ## Format dates
    plt.gcf().autofmt_xdate()
    date_format = mpl_dates.DateFormatter('%d %b. %Y')
    plt.gca().xaxis.set_major_formatter(date_format)

    ## Identifies data point by data on cursor drag
    cursor = mplcursors.cursor(hover=True)
    cursor.connect("add", lambda sel: sel.annotation.set_text("{}\n{}".format(df_sorted[var_list[8]][sel.target.index],df_sorted[var_list[6]][sel.target.index])))

    ## Create figx to save figx as a file in order to use plt.show() (plt.show() removes the plot automatically after being called)
    ## Saves the figure
    figx2 = plt.gcf()
    figx2.savefig(output_dir + '\\' + output_base + '_ColorBars.JPG', facecolor=figx2.get_facecolor(), edgecolor = 'none')
    ## Plots interactive figure
    plt.show(block=False)
    plt.pause(0.1)
    plt.close()

def main():

    ## List site directories for complete image sets here
    filepaths = [
                ## LIST OF DIRECTORIES HOSTING PHOTOS, EACH DIRECTORY NEEDS TO CONTAIN ENTIRE PHOTO SET FOR A STATION
                ]

    ## Loops through site directories
    for filepath in filepaths:

        ## Set working directory
        os.chdir(filepath)

        ## Set output directories
        output_dir = '##FILEPATH TO OUTPUT DIRECTORY' + os.path.basename(os.path.normpath(filepath))
        crop_im_path = output_dir + '\\cropped_images'
        selected_images = output_dir + '\\selected_images'

        ## Make directory for analyses output, selected images, and cropped images
        dirList = ['', '\\selected_images', '\\cropped_images']

        for i in dirList:
            try:
                os.mkdir('##FILEPATH TO OUTPUT DIRECTORY' + os.path.basename(os.path.normpath(filepath)) + i)
            except OSError:
                print ("Creation of the directory failed")
            else:
                print ("Successfully created the directory")

        ## Set output base file name
        output_base = os.path.basename(os.path.normpath(filepath) + '_ColorStats')

        ## Sets variable list
        var_list = ['R mean', 'G mean', 'B mean', 'R std', 'G std', 'B std', 'Date', 'Timestamp', 'Filename', 'Y', 'I', 'Q', 'H', 'L', 'S', 'Hue', 'Saturation', 'Value', 'Contour Count', 'VIGreen', 'VARI', 'vNDVI', 'Hue_Degrees']
        var_list2 = ['R SMA 5', 'G SMA 5', 'B SMA 5', 'Y SMA 5', 'I SMA 5', 'Q SMA 5', 'H SMA 5', 'L SMA 5', 'S SMA 5', 'H2 SMA 5', 'S2 SMA 5', 'L SMA 5', 'Counter SMA 5', 'VIGreen SMA 5', 'VARI SMA 5', 'vNDVI SMA 5']

        # var_list[0],  # R mean    # var_list[1],  # G mean    # var_list[2],  # B mean    # var_list[3],  # R std    # var_list[4],  # G std    # var_list[5],  # B std
        # var_list[6],  # Date      # var_list[7],  # Timestamp # var_list[8],  # Filename  # var_list[9],  # Y        # var_list[10], # I        # var_list[11], # Q
        # var_list[12], # H         # var_list[13], # L         # var_list[14], # S         # var_list[15], # Hue      # var_list[16], # Saturation
        # var_list[17], # Value     # var_list[18], # Contour Count                         # var_list[19], # VIGreen  # var_list[20], #VARI      # var_list[21], # vNDVI
        # var_list[22], # Hue Degrees

        ## Creates and populates df (and creates cropped images and copies of selected images)
        df = processImages(filepath, crop_im_path, selected_images, var_list)

        ## Adds 5-day moving averages to df
        df_sorted = movingAverage(df, var_list, var_list2)

        ## Creates workbook and opens workbook to write df to
        createXLSX(output_dir, output_base, df_sorted)

        ## Per Warning that auto date conversion will not occur unless this function is called
        ## Warning thrown from matplotlib when trying to show plots if register_matplotlib_converters() is not called
        register_matplotlib_converters()

        ## Calls function to produce plots for:
        ## RGB w/ standard deviation
        RGBPlot_std(output_dir, output_base, var_list, df_sorted)
        ## RGB, YIQ, HLS, HSV, RGB Std
        multiPlot(output_dir, output_base, var_list, var_list2, df_sorted)
        ## Contour Count plots
        singlePlot(output_dir, output_base, var_list, var_list2, df_sorted)
        ## Color bars
        ColorBars(output_dir, output_base, var_list, df_sorted)

    pass

if __name__ == '__main__':
    main()
