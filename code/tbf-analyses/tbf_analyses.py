#### This code was used for time-between-failure (TBF) analysis in the following paper:
## George Ostrouchov, Don Maxwell, Rizwan A. Ashraf, Christian Engelmann, Mallikarjun Shankar, and James H. Rogers. 2020. GPU Lifetimes on Titan Supercomputer: Survival Analysis and Reliability. In Proceedings of the International Conference for High Performance Computing, Networking, Storage and Analysis (SC '20). Association for Computing Machinery, New York, NY, USA.
## ...
#### If using this code or this work, please cite the above paper in your work.


#### This code reads in a csv file with GPU failure data and does the following:
## 1. GPU-wise mean-time-between-failure (MTBF) analyses (see Fig-6 in paper).
## 2. System-wide mean-time-between-failure analyses over lifetime (see Fig-7 through 9 in paper).
## Note: currently, system-wide MTBF lifetime analysis is done over quarters (Jan-Mar, Apr-Jun, ...). It can be easily modified to be done over months or years. Moreover, GPU-wise MTBFs can be easily calculated based on locations in the machine (cages, columns, rows).  
####

#### last modified: 2020-06-04 ##################################################################

#### package imports ############################################################################
## for data parsing 
import csv
import time
from datetime import datetime
import re

## for plots and fitting
import numpy as np
import matplotlib.pyplot as plt

#### helper functions for parsing temporal data #################################################
## takes time string input and convert to epoch
def epoch(timestring):
    return int(time.mktime(time.strptime(timestring, "%Y-%m-%d %H:%M:%S")))

def convertToTime(timestring):  
    return time.strptime(timestring, "%Y-%m-%d %H:%M:%S")

#### Parse failure data #########################################################################
## Populate various data-structures for use in analysis later on.
## The following are recorded below:
## failure times and type of failure (DBE: double bit error, or OTB: off-the-bus failure), 
## insert times to calculate time to first failure (in some cases, insert times need to be gathered
## from clean records based on location in the system. See input data for examples).

# file path where csv file is located
CSV_FILE_LOCATION = '../../data/gc_full.csv'

# for time-wise breakdown of TBF (system-wide MTBF analysis)
ALL_RAW_DBE_DATETIMES = [] # includes both new and old batch
ALL_RAW_OTB_DATETIMES = [] 

ALL_DBE_EPOCHS = [] # epoch: see https://www.epochconverter.com/ 
ALL_OTB_EPOCHS = []

ALL_RAW_DBE_dict = {} # these are later used to form old/new sets
ALL_RAW_OTB_dict = {}

# GPU-wise TBF 
DBE_TBF_GPUwise = [] # includes both new and old
OTB_TBF_GPUwise = []

# records start-times (multiple in some cases) and event-times
# start-times are indicated with a record of -1
DBE_dict_GPUwise = {}
OTB_dict_GPUwise = {}
clean_dict_GPUwise = {}  # nor DBE or OTB

# records start-times GPU-wise for old-new analysis later on
oldNew_dict_GPUwise = {}
oldNew_cutoff_epoch = 1451620140 # January 1, 2016 3:49:00 AM

TOTAL_NODES = 18688

# record bad data, write to file at end
bad_data_serials_set = set([])
bad_data_repeat = []

# for accounting only.
DBE_count = 0
OTB_count = 0

### All data is parsed in the loop below.
## csv file: row[0] serial number, row[1] location, row[2] insert datetime, row[3] remove datetime, 
##           row[4] duration (seconds between insert and remove), 
##           row[5] indicates whether the GPU was seen after remove (true/false), 
##           row[6] event_type (DBE/OTB/None).
with open (CSV_FILE_LOCATION) as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    line_count = 0
    for row in csv_reader:
        if line_count == 0: # skip header
            line_count += 1
            continue
        else:
            ### *** DBE *** ###
            if row[6] == 'DBE':
                ### 1a. time-break down analysis
                DBE_count += 1
                if row[3] == "":
                    print('ERROR: empty remove/event date encountered')
                ALL_RAW_DBE_DATETIMES.append(convertToTime(row[3]))
                ALL_DBE_EPOCHS.append(epoch(row[3]))
                # for old/new
                if row[0] in ALL_RAW_DBE_dict: # already in dict
                    ALL_RAW_DBE_dict[row[0]].append(row[3])
                else:
                    ALL_RAW_DBE_dict[row[0]] = [row[3]]

                ### 1b. GPUwise analysis
                if row[2] == "":  # no insert datetime
                    # check various dictionaries for loc match and start time
                    if row[0] in DBE_dict_GPUwise and DBE_dict_GPUwise[row[0]].count(row[1]) > 0:
                        DBE_dict_GPUwise[row[0]].insert(DBE_dict_GPUwise[row[0]].index(row[1])+2, epoch(row[3]))
                        
                    elif row[0] in OTB_dict_GPUwise and OTB_dict_GPUwise[row[0]].count(row[1]) > 0: # check OTB for start time
                        temp = OTB_dict_GPUwise[row[0]].index(row[1])  # NOTE: this returns first occurrence only. 
                        start_temp = OTB_dict_GPUwise[row[0]][temp+1]
                        if row[0] in DBE_dict_GPUwise: # already exists
                            DBE_dict_GPUwise[row[0]].append(row[1])
                            DBE_dict_GPUwise[row[0]].append(start_temp)
                            DBE_dict_GPUwise[row[0]].append(epoch(row[3]))
                        else:
                            DBE_dict_GPUwise[row[0]] = [row[1], start_temp, epoch(row[3])] # start time taken from OTB
                        
                    elif row[0] in clean_dict_GPUwise and clean_dict_GPUwise[row[0]].count(row[1]) > 0: # check no fail for start time
                        temp = clean_dict_GPUwise[row[0]].index(row[1]) # loc match
                        start_temp = clean_dict_GPUwise[row[0]][temp+1]
                        if row[0] in DBE_dict_GPUwise: # already exists
                            DBE_dict_GPUwise[row[0]].append(row[1])
                            DBE_dict_GPUwise[row[0]].append(start_temp)
                            DBE_dict_GPUwise[row[0]].append(epoch(row[3]))
                        else:
                            DBE_dict_GPUwise[row[0]] = [row[1], start_temp, epoch(row[3])]
                        
                    else:
                        # record GPU serial number whose insert time was not found for a particular location.
                        bad_data_serials_set.add((row[0],row[1]))

                else: # insert datetime present
                    # dict already contains row[0]
                    if row[0] in DBE_dict_GPUwise:
                        DBE_dict_GPUwise[row[0]].append(row[1])
                        DBE_dict_GPUwise[row[0]].append(epoch(row[2]))
                        DBE_dict_GPUwise[row[0]].append(epoch(row[3])) # append to existing
                    else:
                        DBE_dict_GPUwise[row[0]] = [row[1], epoch(row[2]), epoch(row[3])] # first element 

                    # for old/new analysis                                                                                    
                    if row[0] in oldNew_dict_GPUwise: # already in dict
                        if epoch(row[2]) < oldNew_dict_GPUwise[row[0]]: # smaller than existing                           
                            oldNew_dict_GPUwise[row[0]] = epoch(row[2])
                    else:
                        oldNew_dict_GPUwise[row[0]] = epoch(row[2])    

            ### *** OTB *** ###
            if row[6] == 'OTB':
                ### 1a. time-break down analysis
                OTB_count += 1
                if row[3] == '':
                    print('ERROR: empty remove/event date encountered')
                ALL_RAW_OTB_DATETIMES.append(convertToTime(row[3]))
                ALL_OTB_EPOCHS.append(epoch(row[3]))
                # for old/new
                if row[0] in ALL_RAW_OTB_dict: # already in dict
                    ALL_RAW_OTB_dict[row[0]].append(row[3])
                else:
                    ALL_RAW_OTB_dict[row[0]] = [row[3]]

                ### 1b. GPUwise analysis
                if row[2] == "": # no insert datetime 
                    # check various dictionaries for loc match and start time
                    if row[0] in OTB_dict_GPUwise and OTB_dict_GPUwise[row[0]].count(row[1]) > 0:
                        OTB_dict_GPUwise[row[0]].insert(OTB_dict_GPUwise[row[0]].index(row[1])+2, epoch(row[3]))
                    
                    elif row[0] in DBE_dict_GPUwise and DBE_dict_GPUwise[row[0]].count(row[1]) > 0: # check DBE for start time
                        temp = DBE_dict_GPUwise[row[0]].index(row[1]) # NOTE: this returns first occurrence only!
                        start_temp = DBE_dict_GPUwise[row[0]][temp+1]
                        if row[0] in OTB_dict_GPUwise: # already exists
                            OTB_dict_GPUwise[row[0]].append(row[1])
                            OTB_dict_GPUwise[row[0]].append(start_temp)
                            OTB_dict_GPUwise[row[0]].append(epoch(row[3]))
                        else:
                            OTB_dict_GPUwise[row[0]] = [row[1], start_temp, epoch(row[3])] # start time taken from DBE

                    elif row[0] in clean_dict_GPUwise and clean_dict_GPUwise[row[0]].count(row[1]) > 0: # check no fail for start time
                        temp = clean_dict_GPUwise[row[0]].index(row[1]) # loc match
                        start_temp = clean_dict_GPUwise[row[0]][temp+1]
                        if row[0] in OTB_dict_GPUwise: # already exists
                            OTB_dict_GPUwise[row[0]].append(row[1])
                            OTB_dict_GPUwise[row[0]].append(start_temp)
                            OTB_dict_GPUwise[row[0]].append(epoch(row[3]))
                        else:
                            OTB_dict_GPUwise[row[0]] = [row[1], start_temp, epoch(row[3])]
                        
                    else:
                        # record GPU serial number whose insert time was not found for a particular location.
                        bad_data_serials_set.add((row[0],row[1]))
                                                
                else: # insert datetime present
                    # dict already contains row[0]                                                                          
                    if row[0] in OTB_dict_GPUwise:
                        OTB_dict_GPUwise[row[0]].append(row[1])
                        OTB_dict_GPUwise[row[0]].append(epoch(row[2]))
                        OTB_dict_GPUwise[row[0]].append(epoch(row[3])) # append to existing                                 
                    else:
                        OTB_dict_GPUwise[row[0]] = [row[1], epoch(row[2]), epoch(row[3])] # first element
            
                    # for old/new analysis
                    if row[0] in oldNew_dict_GPUwise: # already in dict
                        if epoch(row[2]) < oldNew_dict_GPUwise[row[0]]: # smaller than existing
                            oldNew_dict_GPUwise[row[0]] = epoch(row[2])
                    else:
                        oldNew_dict_GPUwise[row[0]] = epoch(row[2])

            ### *** no event: clean *** ### 
            if row[6] == '':
                if row[0] in clean_dict_GPUwise:
                    clean_dict_GPUwise[row[0]].append(row[1]) # loc is saved for match
                    clean_dict_GPUwise[row[0]].append(epoch(row[2]))
                else:
                    clean_dict_GPUwise[row[0]] = [row[1], epoch(row[2])]

                # for old/new analysis
                if row[0] in oldNew_dict_GPUwise: # already in dict
                    if epoch(row[2]) < oldNew_dict_GPUwise[row[0]]: # smaller than existing 
                        oldNew_dict_GPUwise[row[0]] = epoch(row[2])
                else:
                    oldNew_dict_GPUwise[row[0]] = epoch(row[2])

            line_count += 1

    print('Parsed ', line_count, 'lines')
    print('Found', DBE_count, ' DBE events; ', OTB_count, ' OTB events;\n\n')

print ('Number of GPU SNs found: ', len(oldNew_dict_GPUwise), '\n')

#### Create old/new sets for DBE and OTB DATETIME/EPOCH #####################################
ALL_RAW_DBE_DATETIMES__new = []  # to diff. old and new
ALL_RAW_DBE_DATETIMES__old = []
ALL_RAW_OTB_DATETIMES__new = []  # to diff. old and new
ALL_RAW_OTB_DATETIMES__old = []

ALL_DBE_EPOCHS__new = []         # to diff. old and new
ALL_DBE_EPOCHS__old = []
ALL_OTB_EPOCHS__new = []         # to diff. old and new
ALL_OTB_EPOCHS__old = []

### Compare earliest insert time of each GPU with cutoff epoch for each failure type,
### and populate data-structures for use in analysis later on.

### *** 1. DBE *** ###
for i in ALL_RAW_DBE_dict:
    old = -1
    new = -1
    if i in oldNew_dict_GPUwise:
        if oldNew_dict_GPUwise[i] < oldNew_cutoff_epoch: # use cutoff epoch to decide new or old                          
            old = 1
            new = 0
        else:
            new = 1
            old = 0
    else:
        print('ERR: old/new record not found during DBE RAW formation for GPU: ', i)

    if (old >= 0 and new >= 0):
        for val in ALL_RAW_DBE_dict[i]:
            if old == 1:
                ALL_RAW_DBE_DATETIMES__old.append(convertToTime(val))
                ALL_DBE_EPOCHS__old.append(epoch(val))
            elif new == 1:
                ALL_RAW_DBE_DATETIMES__new.append(convertToTime(val))
                ALL_DBE_EPOCHS__new.append(epoch(val))
            else:
                print('ERR: logic issue while separating old and new DBE RAW data for GPU: ', i)
    else:
        print('ERR: logic issue while separating old and new DBE RAW data for GPU: ', i)

### *** 2. OTB *** ###
for i in ALL_RAW_OTB_dict:
    old = -1
    new = -1
    if i in oldNew_dict_GPUwise:
        if oldNew_dict_GPUwise[i] < oldNew_cutoff_epoch:
            old = 1
            new = 0
        else:
            new = 1
            old = 0
    else:
        print('ERR: old/new record not found during OTB RAW formation for GPU: ', i)

    if (old >= 0 and new >= 0):
        for val in ALL_RAW_OTB_dict[i]:
            if old == 1:
                ALL_RAW_OTB_DATETIMES__old.append(convertToTime(val))
                ALL_OTB_EPOCHS__old.append(epoch(val))
            elif new == 1:
                ALL_RAW_OTB_DATETIMES__new.append(convertToTime(val))
                ALL_OTB_EPOCHS__new.append(epoch(val))
            else:
                print('ERR: logic issue while separating old and new OTB RAW data for GPU: ', i)
    else:
        print('ERR: logic issue while separating old and new OTB RAW data for GPU: ', i)

#### PART A: TBF Analysis #####################################################################
cnode = 'c\d+-\d+c(\d)+s\d+n\d+'  # GPU location, see paper: Section III (pgs. 3 & 4)

### Take simple difference of successive failure (DBE, OTB) times.

### *** 1. DBE *** ###
DBE_TBF_dict_GPUwise = {}

for i in DBE_dict_GPUwise:

    times = []
    new = []
    first = 1 # for 2D list

    for val in DBE_dict_GPUwise[i]:
        if isinstance(val, str) and re.match(cnode, val):
            if first == 1:
                first = 2
            else:
                new.sort() # append sorted epoch list
                res = [new[ii] - new[ii-1] for ii in range(1, len(new))]  # take difference of successive times
                times.append(res)

            new = [] # reset inner list
        else:
            new.append(val) # append to inner list

    new.sort() # append sorted epoch list
    res = [new[ii] - new[ii-1] for ii in range(1, len(new))]  # take difference of successive times
    times.append(res) # append last set of times
    # populate dict, everything should be unique
    DBE_TBF_dict_GPUwise[i] = times
    
### *** 2. OTB *** ###
OTB_TBF_dict_GPUwise = {}

for i in OTB_dict_GPUwise:

    times = []
    new = []
    first = 1 # for 2D list
    
    for val in OTB_dict_GPUwise[i]:
        if isinstance(val, str) and re.match(cnode, val):
            if first == 1:
                first = 2
            else:
                new.sort() # append sorted epoch list                                                                        
                res = [new[ii] - new[ii-1] for ii in range(1, len(new))]  # take difference of successive times              
                times.append(res)
                
            new = [] # reset inner list
        else:
            new.append(val) # append to inner list

    new.sort() # append sorted epoch list
    res = [new[ii] - new[ii-1] for ii in range(1, len(new))]  # take difference of successive times
    times.append(res) # append last set of times 
    # populate dict, everything should be unique
    OTB_TBF_dict_GPUwise[i] = times

#### Calculate MTBF for each GPU #######################################################################
MTBF_DBE_GPUwise__old = []
MTBF_DBE_GPUwise__new = []
MTBF_OTB_GPUwise__old = []
MTBF_OTB_GPUwise__new = []

### *** 1. DBE *** ###
for i in DBE_TBF_dict_GPUwise:
    mean = 0.0
    count = 0
    for val in DBE_TBF_dict_GPUwise[i]:
        for tbf in val: 
            mean += tbf
            if tbf <= 0:  # check repeat entries (BAD DATA)
                bad_data_repeat.append((i, 'DBE')) # record serial of GPU with some or all repeat entries
            else:
                count += 1

    # old/new separation
    if i in oldNew_dict_GPUwise:
        if oldNew_dict_GPUwise[i] < oldNew_cutoff_epoch: 
            MTBF_DBE_GPUwise__old.append(mean/count)
        else:
            MTBF_DBE_GPUwise__new.append(mean/count)
    else:
        print('ERR: old/new record not found during DBE TBF formation for GPU: ', i)

### *** 2. OTB *** ###
for i in OTB_TBF_dict_GPUwise:
    mean = 0.0
    count = 0
    for val in OTB_TBF_dict_GPUwise[i]:
        for tbf in val:
            mean += tbf
            if tbf <= 0:  # check repeat entries (BAD DATA)
                bad_data_repeat.append((i, 'OTB')) 
            else:
                count += 1

    # old/new separation
    if i in oldNew_dict_GPUwise:
        if oldNew_dict_GPUwise[i] < oldNew_cutoff_epoch: # 
            MTBF_OTB_GPUwise__old.append(mean/count)
        else:
            MTBF_OTB_GPUwise__new.append(mean/count)
    else:
        print('ERR: old/new record not found during OTB TBF formation for GPU: ', i)

### Convert MTBF to years for each GPU
MTBF_DBE_GPUwise_yrs__old = [x/(60*60*8760) for x in MTBF_DBE_GPUwise__old]
MTBF_DBE_GPUwise_yrs__new = [x/(60*60*8760) for x in MTBF_DBE_GPUwise__new]
MTBF_OTB_GPUwise_yrs__old = [x/(60*60*8760) for x in MTBF_OTB_GPUwise__old]
MTBF_OTB_GPUwise_yrs__new = [x/(60*60*8760) for x in MTBF_OTB_GPUwise__new]

### *** fig-6 SC20 paper. See page 6 *** Distribution of device-level MTBFs ###
plt.figure(figsize=(16,8))

# each bin is approx 2 weeks.
plt.hist([MTBF_DBE_GPUwise_yrs__old, MTBF_OTB_GPUwise_yrs__old], density=False, color=['b','olive'], 
         rwidth=0.8, bins=156, range=[0, 6], label=['Old GPUs: DBE data','Old GPUs: OTB data'])

plt.hist([MTBF_DBE_GPUwise_yrs__new, MTBF_OTB_GPUwise_yrs__new], density=False, color=['blue','olive'], alpha=0.5,
         edgeColor='yellow', linewidth=0.8, rwidth=0.8, bins=156, range=[0, 6], 
         label=['New GPUs: DBE data','New GPUs: OTB data'])

plt.ylabel('Count', fontsize=14)
plt.xlabel('MTBF (years)', fontsize=14)
 
plt.xticks(fontsize=14)
plt.yticks(fontsize=14)
plt.legend(fontsize=14)

plt.tight_layout()

plt.savefig('../../figs/MTBF_GPUwise_yrs_OldNew.pdf', dpi=600)

#### PART B: Time sliced System-wide MTBF Analysis #####################################################

### helper functions for time-slice analysis ###########################

## slice time of type 'time.struct_time'
## the input does not need to be sorted.
## a dictionary is produced at the output, which contains number of cases to analyze for MTBF analysis
def TimeSlicer(theTimes, byYear=True, byMonth=False):
    DictSlicer = {}
    
    if byYear == True:
        for item in theTimes:
            if item.tm_year in DictSlicer:
                DictSlicer[item.tm_year] += 1
            else:
                DictSlicer[item.tm_year] = 1
    
    if byMonth == True:
        for item in theTimes:
            if str(item.tm_year)+'_'+str(item.tm_mon) in DictSlicer:
                DictSlicer[str(item.tm_year)+'_'+str(item.tm_mon)] += 1
            else:
                DictSlicer[str(item.tm_year)+'_'+str(item.tm_mon)] = 1
                 
    return DictSlicer


## input: this helper function takes the output from 'TimeSlicer()' function
## output: 1) sorted list of years of data analyzed, 
## output: 2) based on input: produces a list of list containing number of elements to analyze sorted by time
def SortTimeSlicer(theDict, byYear=True, byMonth=False, byQuarter=False):
    
    years = []
    sortedYrs = []
    
    keylist = theDict.keys()
    
    if byMonth== True or byQuarter== True:
        for item in keylist:
            years.append(item.split('_')[0])
        sortedYrs = sorted(set(years))
    else:
        sortedYrs = sorted(set(keylist))
    
    overallCounts = []
    if byMonth == True:
        for item in sortedYrs:
            countsByMonth = []
            # go through months in order
            if item+'_'+'1' in theDict:
                countsByMonth.append(theDict[item+'_'+'1'])
            else:
                countsByMonth.append(0)
            if item+'_'+'2' in theDict:
                countsByMonth.append(theDict[item+'_'+'2'])
            else:
                countsByMonth.append(0)
            if item+'_'+'3' in theDict:
                countsByMonth.append(theDict[item+'_'+'3'])
            else:
                countsByMonth.append(0)
            if item+'_'+'4' in theDict:
                countsByMonth.append(theDict[item+'_'+'4'])
            else:
                countsByMonth.append(0)
            if item+'_'+'5' in theDict:
                countsByMonth.append(theDict[item+'_'+'5'])
            else:
                countsByMonth.append(0) 
            if item+'_'+'6' in theDict:
                countsByMonth.append(theDict[item+'_'+'6'])
            else:
                countsByMonth.append(0)
            if item+'_'+'7' in theDict:
                countsByMonth.append(theDict[item+'_'+'7'])
            else:
                countsByMonth.append(0)
            if item+'_'+'8' in theDict:
                countsByMonth.append(theDict[item+'_'+'8'])
            else:
                countsByMonth.append(0)
            if item+'_'+'9' in theDict:
                countsByMonth.append(theDict[item+'_'+'9'])
            else:
                countsByMonth.append(0)
            if item+'_'+'10' in theDict:
                countsByMonth.append(theDict[item+'_'+'10'])
            else:
                countsByMonth.append(0)
            if item+'_'+'11' in theDict:
                countsByMonth.append(theDict[item+'_'+'11'])
            else:
                countsByMonth.append(0)
            if item+'_'+'12' in theDict:
                countsByMonth.append(theDict[item+'_'+'12'])
            else:
                countsByMonth.append(0)
    
            overallCounts.append(countsByMonth)
    elif byQuarter==True:
        for item in sortedYrs:
            countsByQuarter = []
            # go through months in order
            Q1count = 0
            if item+'_'+'1' in theDict:
                Q1count += theDict[item+'_'+'1']
            if item+'_'+'2' in theDict:
                Q1count += theDict[item+'_'+'2']
            if item+'_'+'3' in theDict:
                Q1count += theDict[item+'_'+'3']
            # end of quarter
            countsByQuarter.append(Q1count)
            Q2count = 0
            if item+'_'+'4' in theDict:
                Q2count += theDict[item+'_'+'4']
            if item+'_'+'5' in theDict:
                Q2count += theDict[item+'_'+'5']
            if item+'_'+'6' in theDict:
                Q2count += theDict[item+'_'+'6']
            # end of quarter
            countsByQuarter.append(Q2count)
            Q3count = 0
            if item+'_'+'7' in theDict:
                Q3count += theDict[item+'_'+'7']
            if item+'_'+'8' in theDict:
                Q3count += theDict[item+'_'+'8']
            if item+'_'+'9' in theDict:
                Q3count += theDict[item+'_'+'9']
            # end of quarter
            countsByQuarter.append(Q3count)
            Q4count = 0
            if item+'_'+'10' in theDict:
                Q4count += theDict[item+'_'+'10']
            if item+'_'+'11' in theDict:
                Q4count += theDict[item+'_'+'11']
            if item+'_'+'12' in theDict:
                Q4count += theDict[item+'_'+'12']
            # end of quarter
            countsByQuarter.append(Q4count)
            
            overallCounts.append(countsByQuarter)
    else:  # if byYear
        for item in sortedYrs:
            countsByYears = []
            if item in theDict:
                countsByYears.append(theDict[item])
            else:
                countsByYears.append(0)
            
            overallCounts.append(countsByYears)
    
    return (sortedYrs, overallCounts)
            

## calculate the mean time b/w failure -- at system level, sliced by time
## input: this helper function takes list of list output produced by SortTimeSlicer() function
##      : change this input to obtain different time slicing
## input: a sorted list of epoch times (absolute) when failures occur 
## output: list output with MTBF
## output: list of list with raw TBFs
def calcTimeSlicedMTBF(sortedFailTimes, slicer):
    ## ignore the naming of variables, this function can be used for any failure type
    TBF_DBEs_sliced = []
    MTBF_DBE_sys_sliced = [] 
    running_idx = 0
    for j in range(len(slicer)):
        for k in range(len(slicer[j])):
            TBF_DBEs = []
            MTBF_DBE_sys = 0.0
            # below assumes equal number of elements in each sub-list 
            for idx in range(slicer[j][k]):
                if idx == 0: ## skip the first 
                    continue
                diff = sortedFailTimes[running_idx + idx] - sortedFailTimes[running_idx + idx - 1]
                TBF_DBEs.append(diff)  # diff should not be zero here, due to data processing done earlier.
                MTBF_DBE_sys += diff
            
            running_idx += slicer[j][k]
            
            if len(TBF_DBEs) == 0:
                MTBF_DBE_sys_sliced.append(float("inf"))
            else:
                MTBF_DBE_sys_sliced.append(MTBF_DBE_sys/len(TBF_DBEs))  
            TBF_DBEs_sliced.append(TBF_DBEs)

    return (MTBF_DBE_sys_sliced, TBF_DBEs_sliced)

### data conditioning for plots
## input: overallCounts is a list of lists based off byMonth or byQuarter outputs
## output: produces a 1D list to be used for plotting
def plotCountDataConditioner(overallCounts):
    outCounts = []
    for i in range(len(overallCounts)):
        for j in range(len(overallCounts[i])):
            outCounts.append(overallCounts[i][j])
    
    return outCounts

#### track number of new GPUs over time ################################################
ALL_RAW_DATETIMES__new = []

for i in oldNew_dict_GPUwise:
    if oldNew_dict_GPUwise[i] >= oldNew_cutoff_epoch: 
        # Convert a time expressed in seconds since the epoch to a struct_time in UTC
        ALL_RAW_DATETIMES__new.append(time.gmtime(oldNew_dict_GPUwise[i]))

byMonthOutput_num__new = TimeSlicer(ALL_RAW_DATETIMES__new, byYear=False, byMonth=True)
new_yrs, overall_Counts_Quarters_num__new = SortTimeSlicer(byMonthOutput_num__new, byYear=False, byMonth=False, byQuarter=True)

# DBExOTB formed by union of DBE and OTB sets
ALL_RAW_DBExOTB_DATETIMES = set(ALL_RAW_DBE_DATETIMES).union(set(ALL_RAW_OTB_DATETIMES))
# DBExOTB formed by union of DBE and OTB sets  -- REDO for new/old  
ALL_RAW_DBExOTB_DATETIMES__new = set(ALL_RAW_DBE_DATETIMES__new).union(set(ALL_RAW_OTB_DATETIMES__new))
ALL_RAW_DBExOTB_DATETIMES__old = set(ALL_RAW_DBE_DATETIMES__old).union(set(ALL_RAW_OTB_DATETIMES__old))

### *** 1. DBE *** ###
## slice by Months
byMonthOutput_DBEs = TimeSlicer(set(ALL_RAW_DBE_DATETIMES), byYear=False, byMonth=True)
_, overall_Counts_Months_DBEs = SortTimeSlicer(byMonthOutput_DBEs, byYear=False, byMonth=True, byQuarter=False)
## slice by Quarters
_, overall_Counts_Quarters_DBEs = SortTimeSlicer(byMonthOutput_DBEs, byYear=False, byMonth=False, byQuarter=True)

### *** 2. OTB *** ###
## slice by Months
byMonthOutput_OTBs = TimeSlicer(set(ALL_RAW_OTB_DATETIMES), byYear=False, byMonth=True)
_, overall_Counts_Months_OTBs = SortTimeSlicer(byMonthOutput_OTBs, byYear=False, byMonth=True, byQuarter=False)
## slice by Quarters
_, overall_Counts_Quarters_OTBs = SortTimeSlicer(byMonthOutput_OTBs, byYear=False, byMonth=False, byQuarter=True)

### *** 3. DBE or OTB *** ###
## slice by Months
byMonthOutput_DBExOTBs = TimeSlicer(ALL_RAW_DBExOTB_DATETIMES, byYear=False, byMonth=True)
_, overall_Counts_Months_DBExOTBs = SortTimeSlicer(byMonthOutput_DBExOTBs, byYear=False, byMonth=True, byQuarter=False)
## slice by Quarters
_, overall_Counts_Quarters_DBExOTBs = SortTimeSlicer(byMonthOutput_DBExOTBs, byYear=False, byMonth=False, byQuarter=True)

## REDO for old/new
### *** 1. DBE *** ###
### i. new
## slice by Months
byMonthOutput_DBEs__new = TimeSlicer(set(ALL_RAW_DBE_DATETIMES__new), byYear=False, byMonth=True)
_, overall_Counts_Months_DBEs__new = SortTimeSlicer(byMonthOutput_DBEs__new, byYear=False, byMonth=True, byQuarter=False)
## slice by Quarters
_, overall_Counts_Quarters_DBEs__new = SortTimeSlicer(byMonthOutput_DBEs__new, byYear=False, byMonth=False, byQuarter=True)

### ii. old
## slice by Months
byMonthOutput_DBEs__old = TimeSlicer(set(ALL_RAW_DBE_DATETIMES__old), byYear=False, byMonth=True)
_, overall_Counts_Months_DBEs__old = SortTimeSlicer(byMonthOutput_DBEs__old, byYear=False, byMonth=True, byQuarter=False)
## slice by Quarters
_, overall_Counts_Quarters_DBEs__old = SortTimeSlicer(byMonthOutput_DBEs__old, byYear=False, byMonth=False, byQuarter=True)

### *** 2. OTB *** ###
### i. new
## slice by Months
byMonthOutput_OTBs__new = TimeSlicer(set(ALL_RAW_OTB_DATETIMES__new), byYear=False, byMonth=True)
_, overall_Counts_Months_OTBs__new = SortTimeSlicer(byMonthOutput_OTBs__new, byYear=False, byMonth=True, byQuarter=False)
## slice by Quarters
_, overall_Counts_Quarters_OTBs__new = SortTimeSlicer(byMonthOutput_OTBs__new, byYear=False, byMonth=False, byQuarter=True)

### ii. old
## slice by Months
byMonthOutput_OTBs__old = TimeSlicer(set(ALL_RAW_OTB_DATETIMES__old), byYear=False, byMonth=True)
_, overall_Counts_Months_OTBs__old = SortTimeSlicer(byMonthOutput_OTBs__old, byYear=False, byMonth=True, byQuarter=False)
## c. sliced by Quarters
_, overall_Counts_Quarters_OTBs__old = SortTimeSlicer(byMonthOutput_OTBs__old, byYear=False, byMonth=False, byQuarter=True)

### *** 3. DBE or OTB *** ###
### i. new
## slice by Months
byMonthOutput_DBExOTBs__new = TimeSlicer(ALL_RAW_DBExOTB_DATETIMES__new, byYear=False, byMonth=True)
_, overall_Counts_Months_DBExOTBs__new = SortTimeSlicer(byMonthOutput_DBExOTBs__new, byYear=False, byMonth=True, byQuarter=False)
## slice by Quarters
_, overall_Counts_Quarters_DBExOTBs__new = SortTimeSlicer(byMonthOutput_DBExOTBs__new, byYear=False, byMonth=False, byQuarter=True)

### ii. old
## slice by Months
byMonthOutput_DBExOTBs__old = TimeSlicer(ALL_RAW_DBExOTB_DATETIMES__old, byYear=False, byMonth=True)
_, overall_Counts_Months_DBExOTBs__old = SortTimeSlicer(byMonthOutput_DBExOTBs__old, byYear=False, byMonth=True, byQuarter=False)
## slice by Quarters
_, overall_Counts_Quarters_DBExOTBs__old = SortTimeSlicer(byMonthOutput_DBExOTBs__old, byYear=False, byMonth=False, byQuarter=True)


#### calc. system-wide MTBF for each failure type ####################################################
## sort the absolute times of DBEs and OTBs
sorted_DBEs = sorted(set(ALL_DBE_EPOCHS))
sorted_OTBs = sorted(set(ALL_OTB_EPOCHS))
sorted_DBExOTBs = sorted(set(ALL_DBE_EPOCHS).union(set(ALL_OTB_EPOCHS)))

sorted_DBEs__new = sorted(set(ALL_DBE_EPOCHS__new))
sorted_DBEs__old = sorted(set(ALL_DBE_EPOCHS__old))
sorted_OTBs__new = sorted(set(ALL_OTB_EPOCHS__new))
sorted_OTBs__old = sorted(set(ALL_OTB_EPOCHS__old))
sorted_DBExOTBs__new = sorted(set(ALL_DBE_EPOCHS__new).union(set(ALL_OTB_EPOCHS__new)))
sorted_DBExOTBs__old = sorted(set(ALL_DBE_EPOCHS__old).union(set(ALL_OTB_EPOCHS__old)))

### *** 1. DBE *** ###
MTBF_DBE_sys_Quarters, TBF_DBEs_Quarters = calcTimeSlicedMTBF(sorted_DBEs, overall_Counts_Quarters_DBEs)
### *** 2. OTB *** ###
MTBF_OTB_sys_Quarters, TBF_OTBs_Quarters = calcTimeSlicedMTBF(sorted_OTBs, overall_Counts_Quarters_OTBs)
### *** 3. DBE or OTB *** ###
MTBF_DBExOTB_sys_Quarters, TBF_DBExOTBs_Quarters = calcTimeSlicedMTBF(sorted_DBExOTBs, overall_Counts_Quarters_DBExOTBs)

#### calc. MTBF for each failure type -- REDO: diff b/w old and new
### *** 1. DBE *** ###
### i. new
MTBF_DBE_sys_Quarters__new, TBF_DBEs_Quarters__new = calcTimeSlicedMTBF(sorted_DBEs__new, overall_Counts_Quarters_DBEs__new)
### ii. old
MTBF_DBE_sys_Quarters__old, TBF_DBEs_Quarters__old = calcTimeSlicedMTBF(sorted_DBEs__old, overall_Counts_Quarters_DBEs__old)

### *** 2. OTB *** ###
### i. new
MTBF_OTB_sys_Quarters__new, TBF_OTBs_Quarters__new = calcTimeSlicedMTBF(sorted_OTBs__new, overall_Counts_Quarters_OTBs__new)
### ii. old
MTBF_OTB_sys_Quarters__old, TBF_OTBs_Quarters__old = calcTimeSlicedMTBF(sorted_OTBs__old, overall_Counts_Quarters_OTBs__old)

### *** 1. DBE or OTB *** ###
### i. new
MTBF_DBExOTB_sys_Quarters__new, TBF_DBExOTBs_Quarters__new = calcTimeSlicedMTBF(sorted_DBExOTBs__new, overall_Counts_Quarters_DBExOTBs__new)
### ii. old
MTBF_DBExOTB_sys_Quarters__old, TBF_DBExOTBs_Quarters__old = calcTimeSlicedMTBF(sorted_DBExOTBs__old, overall_Counts_Quarters_DBExOTBs__old)

#### convert MTBF in seconds to hours
MTBF_DBE_sys_Quarters = [x/(60*60) for x in MTBF_DBE_sys_Quarters]
MTBF_OTB_sys_Quarters = [x/(60*60) for x in MTBF_OTB_sys_Quarters]
MTBF_DBExOTB_sys_Quarters = [x/(60*60) for x in MTBF_DBExOTB_sys_Quarters]

#### convert MTBF in seconds to hours -- REDO: diff b/w new and old
MTBF_DBE_sys_Quarters__new = [x/(60*60) for x in MTBF_DBE_sys_Quarters__new]
MTBF_DBE_sys_Quarters__old = [x/(60*60) for x in MTBF_DBE_sys_Quarters__old]
MTBF_OTB_sys_Quarters__new = [x/(60*60) for x in MTBF_OTB_sys_Quarters__new]
MTBF_OTB_sys_Quarters__old = [x/(60*60) for x in MTBF_OTB_sys_Quarters__old]
MTBF_DBExOTB_sys_Quarters__new = [x/(60*60) for x in MTBF_DBExOTB_sys_Quarters__new]
MTBF_DBExOTB_sys_Quarters__old = [x/(60*60) for x in MTBF_DBExOTB_sys_Quarters__old]

### *** fig-7 SC20 paper. See page 7 *** system-wide MTBF over time ###
plt.figure(figsize=(12,6))

# this includes data from 2014-Q1 to 2019-Q2. 2019-Q3 and 2019-Q4 are not included, 
# since the machine was decommissioned at end of 2019-Q2
ind = np.arange(len(MTBF_DBE_sys_Quarters[0:22]))

plt.plot(MTBF_DBE_sys_Quarters[0:22], linestyle='--', marker='o', markersize=10, color='b', lw=2, label='DBE')
plt.plot( MTBF_OTB_sys_Quarters[0:22], linestyle='-', marker='s', markersize=10, color='olive', lw=2, label='OTB')
plt.plot( MTBF_DBExOTB_sys_Quarters[0:22], linestyle=':', marker='X', markersize=10, color='red', lw=2, label='DBE or OTB')

plt.xticks(ind, ('2014-Q1', '2014-Q2', '2014-Q3', '2014-Q4',
                '2015-Q1', '2015-Q2', '2015-Q3', '2015-Q4',
                '2016-Q1', '2016-Q2', '2016-Q3', '2016-Q4',
                '2017-Q1', '2017-Q2', '2017-Q3', '2017-Q4',
                '2018-Q1', '2018-Q2', '2018-Q3', '2018-Q4',
                '2019-Q1', '2019-Q2'), rotation=45, fontsize=12)

plt.legend(fontsize=14)

plt.yticks(fontsize=14)
plt.ylabel('MTBF (hours)', fontsize=14)

plt.tight_layout()

plt.savefig('../../figs/MTBF_quaterly_sys.pdf', dpi=600)

### *** fig-9 SC20 paper. See page 7 *** system-wide MTBF over new and old partitions ###

### prepare num over time for plot starting from 2017-Q1 
proportions = [] # 2017-Q1 to 2019-Q2. the size of the new partition.
temp_sum = 0
idx = 0
flatten__overall_Counts_Quarters_num__new = sum(overall_Counts_Quarters_num__new, [])
for i in range(len(flatten__overall_Counts_Quarters_num__new)):
    if i < 5:
        temp_sum += flatten__overall_Counts_Quarters_num__new[i]
        if i == 4:
            proportions.append(temp_sum)
    elif i > 4 and i < 14:
        proportions.append(proportions[idx]+flatten__overall_Counts_Quarters_num__new[i])
        idx = idx+1

proportions = [(x/TOTAL_NODES)*100 for x in proportions]

### put 'inf' to match data lengths for NEW datasets -- REDO: diff b/w new and old
## 1. DBE (quarters)
plot___MTBF_DBE_sys_Quarters__new = []
for i in range(len(MTBF_DBE_sys_Quarters__old)):
    if i >= 0 and i <= 7:
        plot___MTBF_DBE_sys_Quarters__new.append(float("inf"))
    else:
        plot___MTBF_DBE_sys_Quarters__new.append(MTBF_DBE_sys_Quarters__new[i-8])
### put 'inf' to match data lengths for NEW datasets -- REDO: diff b/w new and old
## 2. OTB (quarters)
plot___MTBF_OTB_sys_Quarters__new = []
for i in range(len(MTBF_OTB_sys_Quarters__old)):
    if i >= 0 and i <= 7:
        plot___MTBF_OTB_sys_Quarters__new.append(float("inf"))
    else:
        plot___MTBF_OTB_sys_Quarters__new.append(MTBF_OTB_sys_Quarters__new[i-8])
## 3. DBE or OTB (quarters)
plot___MTBF_DBExOTB_sys_Quarters__new = []
for i in range(len(MTBF_DBExOTB_sys_Quarters__old)):
    if i >= 0 and i <= 7:
        plot___MTBF_DBExOTB_sys_Quarters__new.append(float("inf"))
    else:
        plot___MTBF_DBExOTB_sys_Quarters__new.append(MTBF_DBExOTB_sys_Quarters__new[i-8])

ind = np.arange(len(MTBF_DBE_sys_Quarters[13:22]))

fig, ax = plt.subplots(figsize=(12,6))
bar_width = 0.25
opacity = 0.8

ind = np.arange(len(MTBF_DBE_sys_Quarters[12:22]))
ind2 = [x + bar_width for x in ind]
ind3 = [x + bar_width for x in ind2]

ax.bar(ind, plot___MTBF_DBExOTB_sys_Quarters__new[12:22], width=bar_width, alpha=opacity*0.25, color='red', label='New GPUs: DBE or OTB')
ax.bar(ind2, MTBF_DBExOTB_sys_Quarters__old[12:22], width=bar_width, alpha=opacity*0.5, color='red', label='Old GPUs: DBE or OTB')
ax.bar(ind3, MTBF_DBExOTB_sys_Quarters[12:22], width=bar_width, alpha=opacity, color='red', label='ALL GPUs: DBE or OTB')

plt.xticks([r + bar_width for r in range(len(MTBF_DBE_sys_Quarters[12:22]))], ('2017-Q1', '2017-Q2', '2017-Q3', '2017-Q4',
                '2018-Q1', '2018-Q2', '2018-Q3', '2018-Q4',
                '2019-Q1', '2019-Q2'), rotation=45, fontsize=12)


ax2 = ax.twinx()  # secondary y-axis  

ax2.plot(ind, proportions, 'r--', marker="X")
ax2.set_ylabel('New batch partition size (% of in-service GPUs)', color='r', fontsize=14)

ax.legend(fontsize=12, loc='upper left')

ax.set_ylabel('MTBF (hours)', fontsize=14)

for label in ax.yaxis.get_majorticklabels():
    label.set_fontsize(14)
for label in ax2.yaxis.get_majorticklabels():
    label.set_fontsize(14)

plt.tight_layout()

plt.savefig('../../figs/MTBF_quaterly_sys_NewOldALL_newPart.pdf', dpi=600)

### *** fig-8 SC20 paper. See page 7 *** Number of DBE and OTB failures over time ###
## condition data for plotting using helper function
plot__overall_Counts_Quarters_DBEs = plotCountDataConditioner(overall_Counts_Quarters_DBEs)
plot__overall_Counts_Quarters_OTBs = plotCountDataConditioner(overall_Counts_Quarters_OTBs)

## Redo old/new data 
### put 'inf' to match data lengths for NEW datasets -- REDO: diff b/w new and old
plot___overall_Counts_Quarters_DBEs__new = []
for i in range(len(overall_Counts_Quarters_DBEs__old)):
    for j in range(len(overall_Counts_Quarters_DBEs__old[i])):
        if i >= 0 and i <=1:
            plot___overall_Counts_Quarters_DBEs__new.append(float('inf'))
        else:
            plot___overall_Counts_Quarters_DBEs__new.append(overall_Counts_Quarters_DBEs__new[i-2][j])

plot__overall_Counts_Quarters_DBEs__old = plotCountDataConditioner(overall_Counts_Quarters_DBEs__old)
plot__overall_Counts_Quarters_OTBs__old = plotCountDataConditioner(overall_Counts_Quarters_OTBs__old)

## do the plot...
plt.figure(figsize=(12,6))

ind = np.arange(len(plot__overall_Counts_Quarters_DBEs[0:22]))    # the x locations for the groups

plt.plot(plot__overall_Counts_Quarters_DBEs[0:22], linestyle='-', marker='X', markersize=10, color='b', lw=2, label='ALL GPUs: DBE')
plt.plot(plot__overall_Counts_Quarters_OTBs[0:22], linestyle='-', marker='o', markersize=10, color='olive', lw=2, label='ALL GPUs: OTB')

plt.plot(plot__overall_Counts_Quarters_DBEs__old[0:22], linestyle=':', marker='<', markersize=6, color='b', lw=1.5, label='Old GPUs: DBE')
plt.plot(plot__overall_Counts_Quarters_OTBs__old[0:22], linestyle=':', marker='v', markersize=6, color='olive', lw=1.5, label='Old GPUs: OTB')

plt.xticks(ind, ('2014-Q1', '2014-Q2', '2014-Q3', '2014-Q4',
                '2015-Q1', '2015-Q2', '2015-Q3', '2015-Q4',
                '2016-Q1', '2016-Q2', '2016-Q3', '2016-Q4',
                '2017-Q1', '2017-Q2', '2017-Q3', '2017-Q4',
                '2018-Q1', '2018-Q2', '2018-Q3', '2018-Q4',
                '2019-Q1', '2019-Q2'), rotation=45, fontsize=12)

plt.ylim(0, 600)
plt.yticks(fontsize=14)
plt.ylabel('Number of Failures', fontsize=14)
plt.legend(fontsize=14)

plt.tight_layout()

plt.savefig('../../figs/NumFailures_Quarterly_newOld.pdf', dpi=600)

#### write bad serial numbers ################################################################
MyFile=open('bad_serials.dat','w')
MyFile.write('# no record for loc insert found for following GPU Serial Numbers:\n')
for element in bad_data_serials_set:
    serial, loc = element
    temp = str(serial), str(loc)
    temp_str = ','.join(temp)
    MyFile.write(temp_str)
    MyFile.write('\n')
MyFile.close()

MyFile2=open('bad_serials_repeat.dat','w')
MyFile2.write('One or more repeat entries found for following GPU Serial Numbers:\n')
for element in bad_data_repeat:
    serial, type = element
    temp = str(serial), type
    temp_str = ','.join(temp)
    MyFile2.write(temp_str)
    MyFile2.write('\n')
MyFile2.close()

