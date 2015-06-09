"""
This script will calculate the double integral of a derivative EPR spectrum.

You should make this dump the spectrum and the double integral to the database with a searchable sample number. This way you could calculate all ODNP + EPR information by looking for you sample.

Bugs:
    1) Script crashed with this file CheY_M17C_P2_202uM_14mm_10db.asc
        a) It cannot find the peaks appropriately
        b) it's too noisy and finds many peaks
        c) it also suffers from finding more than one local maxima in the region.

To Do:
    1) Import bruker .par files - for now will just use the exported ASCII format 
    ** 2) Calculate absorption spectrum
    ** 3) Fit the ends of the absorption spec to a line and subtract the line from the spectrum.
    ** 4) Calculate the double integrated value and check to make sure the end is flat
    5) Add wrappers for finding the file directory - copy from returnIntegrals.py
    6) Add wrappers to dump the data to the database.
    7) Pull in the .par file and dump information to the otherInfo of the database. Use the par file to pull how many scans were run and normalize spectra by the number of scans.
    ** 8) Find the field points that define the edges of the spectrum given a variable linewidth parameter - not yet using variable line width
    ** 9) Drop any values below zero from the absorption spectrum before you integrate. - this may be buggy if there is more than one zero crossing. You might just use you estimate of the edge of the spectrum for this.
    ** 10) Calculate edge peak to peak width.
    ** 11) Calculate spectral line widths.
    ** 12) Calculate the center field
"""
from matlablike import *
close('all')

### Import the files - for now this is hard coded and this only works with ASCII files, you need to change this so you can use the par files as well.
fullPath = '/Users/StupidRobot/exp_data/ryan_cnsi/epr/150122_EPRConcSeries/'
fileName = 'CheY_M17C_P2_202uM_14mm_10db'

# Open the ASCII file and pull the spectrum#{{{
openFile = open(fullPath + fileName + '.asc','r') 
lines = openFile.readlines()
field = []
spec = []
for line in lines:
    try:
        new = line.split('\t')
        field.append(float(new[0]))
        spec.append(float(new[1].split('\r')[0]))
    except:
        print "Skipping header values."
spec = nddata(array(spec)).rename('value','field').labels('field',array(field).round(2))#}}}

##### This does not yet do what is needed for reading from the par file !!!!!!

# Open the par file and pull the relevant parameters #{{{
openFile = open(fullPath + fileName + '.par','r') 
lines = openFile.readlines()
expDict = {}
for line in lines[0].split('\r'):
    try:
        expDict.update({line.split(' ')[0]:line.split(' ')[1]})
    except:
        print "Skipping header values."#}}}

# Find the peaks of the derivative spectrum and calculate spectral width, center field, and bounds on the spectrum accordingly.#{{{

# Find the three largest peaks
# peak 1 find the field value of the zero crossing
peak1 = spec.data.argmax()
valley1 = spec.data.argmin()
#find the high bound
notCrossed=True
count = 0
while notCrossed:
    if float(spec['field',peak1+count].data) <= 0.:
        lowBound = peak1+count
        notCrossed = False
    count-=1
# find the low bound
counts=0
while notCrossed:
    if float(spec['field',valley1+counts].data) >= 0.:
        highBound = valley1+counts
        notCrossed = False
    counts+=1
cut1 = spec['field',lowBound:highBound]
figure()
plot(spec)
plot(cut1)

maxi = spec.data.max()
threshMax = .2*maxi
mini = spec.data.min()
threshMin = 0.2*mini
maximaField = []
maximaData = []
minimaField = []
minimaData = []
for count,value in enumerate(spec.data[1:-1]):
    if (value >= threshMax):
        maximaField.append(spec.getaxis('field')[count])
        maximaData.append(spec.data[count])
    elif (value <= threshMin):
        minimaField.append(spec.getaxis('field')[count])
        minimaData.append(spec.data[count])
maxima = nddata(array(maximaData)).rename('value','field').labels('field',array(maximaField))
minima = nddata(array(minimaData)).rename('value','field').labels('field',array(minimaField))

# Now find the peaks and valleys... To root find or just window? Tis the question... Windowing is probably cleaner...
# Find the breaks and dump into three separate nddatas.
peaksData = []
peaksField = []
for count,value in enumerate(maxima.data[1:-1]):
    if (value > maxima.data[count]) and (value > maxima.data[count+2]):
        peaksField.append(maxima.getaxis('field')[count+1])
        peaksData.append(maxima.data[count+1])
peaks = nddata(array(peaksData)).rename('value','field').labels('field',array(peaksField))
# Here you need to drop all but one local maxima
valleysData = []
valleysField = []
for count,value in enumerate(minima.data[1:-1]):
    if (value < minima.data[count]) and (value < minima.data[count+2]):
        valleysField.append(minima.getaxis('field')[count+1])
        valleysData.append(minima.data[count+1])
valleys = nddata(array(valleysData)).rename('value','field').labels('field',array(valleysField))
lineWidths = peaks.getaxis('field') - valleys.getaxis('field')
spectralWidth = peaks.getaxis('field').max() - peaks.getaxis('field').min() 
centerField = peaks.getaxis('field')[1] + lineWidths[1]/2.# assuming the center point comes out in the center. The way the code is built this should be robust
specStart = centerField - spectralWidth
specStop = centerField + spectralWidth
print "\nI calculate the spectral width to be: ",spectralWidth," G \n"
print "I calculate the center field to be: ",centerField," G \n"
print "I set spectral bounds of: ", specStart," and ", specStop," G \n"

# Baseline correct the spectrum
#baseline1 = spec['field',lambda x: x < specStart].mean('field')
#baseline2 = spec['field',lambda x: x > specStop].mean('field')
#baseline = average(array([baseline1.data,baseline2.data]))
#spec.data -= baseline

# Plot the results
figure()
plot(spec,'m',alpha=0.6)
plot(maxima,'r.')
plot(minima,'g.')
plot(spec['field',lambda x: logical_and(x>specStart,x<specStop)],'b')
title('Integration Window')
ylabel('Spectral Intensity')
xlabel('Field (G)')
#giveSpace(spaceVal=0.01)
tight_layout()

#}}}

### Take the first integral #{{{
absorption = spec.copy().integrate('field')#}}}

# Fit the bounds of the absorption spec to a line and subtract from absorption spectrum.#{{{
baseline1 = absorption['field',lambda x: x < specStart]
baseline2 = absorption['field',lambda x: x > specStop]
fieldBaseline = array(list(baseline1.getaxis('field')) + list(baseline2.getaxis('field')))
baseline = concat([baseline1,baseline2],'field')
baseline.labels('field',fieldBaseline)
c,fit = baseline.polyfit('field',order = 1)
fit = nddata(array(c[0] + absorption.getaxis('field')*c[1])).rename('value','field').labels('field',absorption.getaxis('field'))
correctedAbs = absorption - fit#}}}

# Set the values of absorption spec outside of int window to zero.#{{{
zeroCorr = correctedAbs.copy()
zeroCorr['field',lambda x: x < specStart] = 0.0
zeroCorr['field',lambda x: x > specStop] = 0.0#}}}

# Plot absorption results#{{{
figure()
plot(absorption)
plot(fit)
plot(correctedAbs)
plot(zeroCorr)
title('Absorption Spectrum')
ylabel('Absorptive Signal')
xlabel('Field (G)')
#}}}

# Calculate and plot the double integral for the various corrections you've made #{{{
doubleInt = absorption.copy().integrate('field')
doubleIntC = correctedAbs.copy().integrate('field')
doubleIntZC = zeroCorr.copy().integrate('field')
print "\nI calculate the double integral to be: %0.2f\n"%doubleIntZC.data.max()

figure()
plot(doubleInt,label='uncorrected')
plot(doubleIntC,label='corrected')
plot(doubleIntZC,label='zero corrected')
legend(loc=2)
title('Double Integral Results')
ylabel('Second Integral (arb)')
xlabel('Field (G)')
giveSpace(spaceVal=0.001)
tight_layout()
#}}}

# Write parameters to csv file, right now this is determined by the epr file location. - In future this should be tied to the odnp exp file as part of return integrals.
# parameters to write (1) all from par file, (2) center field, (3) spectral width, (4) double integral value from zero corrected or from baseline fit if not available.


show()



