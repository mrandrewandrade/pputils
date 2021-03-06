#!/usr/bin/env python3
#
#+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!
#                                                                       #
#                                 gis2mesh.py                           # 
#                                                                       #
#+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!+!
#
# Author: Pat Prodanovic, Ph.D., P.Eng.
# 
# Date: November 11, 2016
#
# Purpose: Same as my gis2tin.py, except it uses Triangle to construct
# the quality mesh, which is then converted to an adcirc mesh format. 
# The script also calls the adcirc2shp.py to convert the mesh to a 
# shapefile format, so that it may be viewed on a GIS platform.
#
# Revised: Apr 29, 2017
# Changed how different system architectures are called; made it work
# for the raspberry pi system.
#
# Revised: May 6, 2017
# Placed a call to processor type inside the posix if statement.
#
# Uses: Python 2 or 3, Numpy
#
# Example:
#
# python gis2mesh.py -n nodes.csv -b boundary.csv -l lines.csv -h none -a area.csv -o mesh.grd
#
# where:
#       --> -n is the file listing of all nodes (incl. embedded nodes
#                        if any). The nodes file consist of x,y,z or x,y,z,size;
#                        The size parameter is an optional input, and is used 
#                        by gmsh as an extra parameter that forces element 
#                        size around a particular node. For triangle, it has
#                        no meaning. The nodes file must be comma separated, and
#                        have no header lines. 
#
#       --> -b is the node listing of the outer boundary for the mesh.
#                        The boundary file is generated by snapping lines
#                        to the nodes from the nodes.csv file. The boundary file 
#                        consists of shapeid,x,y of all the lines in the file.
#                        Boundary has to be a closed shape, where first and last 
#                        nodes are identical. Shapeid is a integer, where the
#                        boundary is defined with a distict id (i.e., shapeid 
#                        of 0). 
#
#       --> -l is the node listing of the constraint lines for the mesh.
#                        The lines file can include open or closed polylines.
#                        The file listing has shapeid,x,y, where x,y have to 
#                        reasonable match that of the nodes.csv file. Each distinct
#                        line has to have an individual (integer) shapeid. If no 
#                        constraint lines in the mesh, enter 'none' without the
#                        quotes.
#
#       --> -h is the listing of the holes in the mesh. The holes file is
#                        generated by placing a single node marker inside a
#                        closed line constraint. The holes file must include a 
#                        x,y coordinate within the hole boundary. If no holes
#                        (islands) in the mesh, enter 'none' without the quotes. 
#                        Note that for triangle, the format of the holes file 
#                        is different than for gmsh!!!
#
#       --> -a is the listing of the area constraints in the mesh. The area file is
#                        generated by placing a single node marker inside a
#                        closed line constraint. The areas file must include a 
#                        x,y,area for each area bounded by each area. If 
#                        option for area is 'none' without the quotes, area constraints
#                        are not used.
#
#      --> -o is the output adcirc file that is the quality mesh.
# 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Global Imports
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
import os,sys                              # system parameters
import numpy             as np             # numpy
from collections import OrderedDict        # for removal of duplicate nodes
import struct                              # to determine sys architecture
import subprocess                          # to execute binaries
#
curdir = os.getcwd()
#
try:
  # this only works when the paths are sourced!
  pputils_path = os.environ['PPUTILS']
except:
  pputils_path = curdir
  
  # this is to maintain legacy support
  if (sys.version_info > (3, 0)):
    version = 3
    pystr = 'python3'
  elif (sys.version_info > (2, 7)):
    version = 2
    pystr = 'python'
#
# I/O
if len(sys.argv) == 13 :
  nodes_file = sys.argv[2]
  boundary_file = sys.argv[4]
  lines_file = sys.argv[6]
  holes_file = sys.argv[8]
  areas_file = sys.argv[10]
  output_file = sys.argv[12]
else:
  print('Wrong number of Arguments, stopping now...')
  print('Usage:')
  print('python gis2mesh.py -n nodes.csv -b boundary.csv -l lines.csv -h holes.csv -a areas.csv -o mesh.grd')
  sys.exit()

# to determine if the system is 32 or 64 bit
archtype = struct.calcsize("P") * 8

# call gis2triangle.py
print('Generating Triangle input files ...')
try:
  subprocess.call(['gis2triangle.py', '-n', nodes_file, 
  '-b', boundary_file, '-l', lines_file, '-h', holes_file, 
  '-o', 'mesh.poly'])
except:
  subprocess.call([pystr, 'gis2triangle.py', '-n', nodes_file, 
  '-b', boundary_file, '-l', lines_file, '-h', holes_file, 
  '-o', 'mesh.poly'])

# read areas file
areas_data = np.loadtxt(areas_file, delimiter=',',skiprows=0,unpack=True)

# this is the number of area constraints to add
# find out how many area points are in the area file
num_areas = len(open(areas_file).readlines())
  
# this is not optimal, but rather than changing the gis2triangle_kd.py
# script, read the mesh.poly file, and append the information on the 
# area constraints before running Triangle. This is sloppy, but it works!

with open('mesh.poly', 'a') as f: # 'a' here is for append to the file
  f.write('\n')
  f.write(str(num_areas) + '\n')
  
  # if more than one area constraint node
  if (num_areas == 1):
    f.write('1' + ' ' + str(areas_data[0]) + ' ' +\
        str(areas_data[1]) + ' ' + str(0) + ' ' +\
        str(areas_data[2]) + '\n')
  else:
    for i in range(num_areas):
      f.write(str(i+1) + ' ' + str(areas_data[0,i]) + ' ' +\
        str(areas_data[1,i]) + ' ' + str(0) + ' ' +\
        str(areas_data[2,i]) + '\n')

# now run Triangle
if (os.name == 'posix'):
  # determines processor type
  proctype = os.uname()[4][:]

  # for linux32 its i686
  # for linux64 its x86_64
  # for raspberry pi 32 its armv7l
  
  # this assumes chmod +x has already been applied to the binaries
  if (proctype == 'i686'):
    subprocess.call( [pputils_path + '/triangle/bin/triangle_32', '-Dqa', 'mesh.poly' ] )
  elif (proctype == 'x86_64'):
    subprocess.call( [pputils_path + '/triangle/bin/triangle_64', '-Dqa', 'mesh.poly' ] )
  elif (proctype == 'armv7l'):
    subprocess.call( [pputils_path + '/triangle/bin/triangle_pi32', '-Dqa', 'mesh.poly' ] )
elif (os.name == 'nt'):
  subprocess.call( ['.\\triangle\\bin\\triangle_32.exe', '-Dqa', 'mesh.poly' ] )
else:
  print('OS not supported!')
  print('Exiting!')
  sys.exit()
  
# call triangle2adcirc.py
print('Converting Triangle output to ADCIRC mesh format ...')
try:
  subprocess.call(['triangle2adcirc.py', '-n', 'mesh.1.node', 
    '-e', 'mesh.1.ele', '-o', output_file])
except:
  subprocess.call([pystr, 'triangle2adcirc.py', '-n', 'mesh.1.node', 
    '-e', 'mesh.1.ele', '-o', output_file])

# to remove the temporary files
os.remove('mesh.poly')
os.remove('mesh.1.poly')
os.remove('mesh.1.node')
os.remove('mesh.1.ele')

# construct the output shapefile name (user reverse split function)
wkt_file = output_file.rsplit('.',1)[0] + 'WKT.csv'

# now convert the *.grd file to a *.shp file by calling adcirc2shp.py
print('Converting ADCIRC mesh to wkt format ...')
try:
  subprocess.call(['adcirc2wkt.py', '-i', output_file, '-o', wkt_file])
except:
  subprocess.call([pystr, 'adcirc2wkt.py', '-i', output_file, '-o', wkt_file])

