#!/usr/bin/env python
from __future__ import division
import os
import sys
import json
import rospy
import math
import scipy
from semantic_segmentation.srv import *
import numpy as np
import pylab as pl
import matplotlib.pyplot as plt
from unidecode import unidecode
from scipy.cluster.vq import kmeans,vq
from matplotlib.mlab import PCA
from scipy.optimize import fmin_bfgs, fmin_l_bfgs_b
from mpl_toolkits.mplot3d import Axes3D
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial import distance
import random
from collections import Counter
#from vectors import *
from scipy.spatial import ConvexHull

import roslib; roslib.load_manifest('visualization_marker_tutorials')
from visualization_msgs.msg import Marker
from visualization_msgs.msg import MarkerArray

class identify_region:
    
    def __init__(self,waypoint,instances):
        self.outer_region=dict()
        self.inner_region=dict()
        self.sepcial_object=[]
        self.label=dict()
        self.position_matrix=dict()
        self.prob=dict()
        self.points=dict()
        for instance in instances:
            self.position_matrix[instance]=dict()
            self.prob[instance]=json.load(open('data/'+waypoint+str(instance)+"prob_large.json","r"))
            self.points[instance]=json.load(open('data/'+waypoint+str(instance)+"points_large.json","r"))
            label_names=json.load(open("data/label_names_large.json","r"))
            self.label_names=label_names[waypoint][unicode(0)]
            prob=np.array(self.prob[instance]).reshape(-1,11)
            points=self.points[instance]
            temp=[]
            indexs=prob.argmax(axis=1).tolist()
            for index in indexs:
                temp=temp+[(self.label_names[index])]
            self.label[instance]=temp
            for objects in self.label_names:
                temp=[]
                for i in range(len(self.label[instance])):
                    if self.label[instance][i]==objects:
                       temp=self.points[instance][i]+temp
                self.position_matrix[instance][objects]=np.array(temp).reshape(-1,3)
                
    def random(self,data,n):
        index=random.sample(range(len(data)),n)
        maybe=data[index]
        rest_index=[]
        for i in range(len(data)):
            if i not in index:
               rest_index=rest_index+[i]
        rest=data[rest_index]
        return maybe,rest    

#form a wall given points labelled as wall       
    def fit(self,wall):
        max_index=np.argmax(wall,axis=0)
        min_index=np.argmin(wall,axis=0)
        a=wall[max_index[1]]
        b=wall[min_index[1]]
        c=wall[min_index[0]]
        d=wall[max_index[0]]
        return [a,b,c,d]

#judge the spatial relationship between a point and a line in 2D 
    def vector(self,start,end):
         b=np.array(end)
         a=np.array(start)
         return b-a
    def unit(self,vec):
         return vec/sum(vec**2)
    def add(self,vec,start):
         a=np.array(start)
         return (a+vec).tolist()               
    def pnt2line(self,pnt, start, end):
        inner=1
        line_vec = self.vector(start, end)
        pnt_vec = self.vector(start, pnt)
        line_len = distance.euclidean(start,end)
        line_unitvec = self.unit(line_vec)
        pnt_vec_scaled = pnt_vec*1.0/line_len
        t = sum(line_unitvec*pnt_vec_scaled)    
        if t < 0.0:
           t=0.0
        elif t > 1.0:
           t=1.0
        nearest = (line_vec*t).tolist()
        dist = distance.euclidean(nearest, pnt)
        nearest = self.add(nearest, start)
        return (dist, nearest)

#restrict the range of points that might be in a room
    def selection(self,origin_data,waypoint):
        data=[]
        for i in range(len(origin_data)):
            point=origin_data[i].tolist()
            if distance.euclidean(point,waypoint)<4.0:
               data=data+point
        data=np.array(data).reshape(-1,3)
        return data
#compute the distance between a point and the nearest wall
    def distance(self,point,model):
        dis=[0]*4
        dis[0]=self.pnt2line(point,model[0],model[3])
        dis[1]=self.pnt2line(point,model[3],model[1])
        dis[2]=self.pnt2line(point,model[1],model[2])
        dis[3]=self.pnt2line(point,model[2],model[0])
        dist=min(dis)
        return dist

# using RANSAC to generate a good wall              
    def set_outter_region(self,waypoint,instance,k,draw=0):
        origin_data=np.array(self.position_matrix[instance]['wall'])
        origin_data[:,2]=0
        data=self.selection(origin_data,waypoint)
        iteration=0
        besterr=1
        bestfit=[]
        n=1000
        while iteration<k:
            print iteration
            maybewall,rest=self.random(data,n)
            maybemodel=self.fit(maybewall)
            alsowall=[]
            for point in rest:
                if self.distance(point,maybemodel)<0.5:
                    alsowall=alsowall+point.tolist()
            alsowall=np.array(alsowall).reshape(-1,3)
            print len(alsowall),len(data)
            if len(alsowall)>len(data)/2:
                wall=np.concatenate((maybewall,alsowall),axis=0)
                thiserr=1-float(len(wall))/len(data)
                print wall  
                if thiserr<besterr:
                    bestfit=self.fit(wall)
                    besterr=thiserr
            iteration=iteration+1
        print bestfit
        if draw:
            topic='visualization_marker_array'
            publisher=rospy.Publisher(topic,MarkerArray,queue_size=10)
            rospy.init_node('register',anonymous=True)
            markerArray=MarkerArray()
            i=0
            while i<4:
                    marker = Marker()
                    marker.header.frame_id = "/map"
                    marker.ns="outer_region"
                    marker.type = marker.SPHERE
                    marker.action = marker.ADD
                    marker.scale.x = 0.1
                    marker.scale.y = 0.1
                    marker.scale.z = 0.1
                    marker.color.a = 1.0
                    marker.color.g = 1
                    #marker.color.r = i/10
                    marker.pose.orientation.w = 1.0
                    marker.pose.position.x = bestfit[i][0]
                    marker.pose.position.y = bestfit[i][1]
                    marker.pose.position.z = 0
                    markerArray.markers.append(marker)
                    id_num=0
                    for m in markerArray.markers:
                        m.id=id_num
                        id_num+=1
                    i=i+1
            while not rospy.is_shutdown():
                    publisher.publish(markerArray)
                    rospy.sleep(0.01)
        return bestfit,besterr
        
#judge if the point is in a given direction       
        def online(point,theta,centre):
            if(point-centre)[1]/(point-centre)[0]==math.sin(theta):
                dis=distance.euclidean(point,centre)
            else:
                dis=100
            return dis
#form the space where robot can move freely        
        def set_inner_region(self,waypoint,centre,instance,draw=0):
            chull=[]
            for view in range(36):
                theta=2*pi/view
                dis=100
                for point in self.points[instance]:
                    if self.label[instance][i] == (u'floor' | u'ceilling'):
                        i=0
                    else :
                        temp=online(point,theta,centre)
                        if dis>temp:
                           dis=temp
                           near=point
                chull=chull+near
            chull=np.array(chull).reshape(-1,3)
            chull=np.concatenate((chull,chull[0]),axis=0)
            if draw:
                points=[]
                for i in range(len(chull)):
                   point=Point()
                   point.x=chull[i][0]
                   point.y=chull[i][1]
                   point.z=chull[i][2]
                   points=points+[point]
                topic='visualization_marker'
                publisher=rospy.Publisher(topic,Marker)
                rospy.init_node('actual',anonymous=True)
                while not rospy.is_shutdown():
                        marker = Marker()
                        marker.header.frame_id = "/map"
                        marker.ns="inner_region"
                        marker.id=1
                        marker.type = marker.LINE_STRIP
                        marker.action = marker.ADD
                        marker.scale.x = 0.03
                        marker.color.a = 1.0
                        marker.color.r =1.0
                        marker.points = points
                        publisher.publish(marker)
        
                
                
                


        
if __name__ == "__main__":
   #print 'finding'
   label_type=["prop","wall","cabpip pythoninet","ceiling","chair/sofa", "window", "floor","monitor/tv","person","shelf", "table"]
   #req=json.loads(raw_input('request waypoint & instance'))
   req=[u"WayPoint42",[0]]
   objects=identify_region(unidecode(req[0]),req[1])
   #objects.bounding_box(unidecode(req[0]),req[1],label_type[4]) 
   objects.set_outter_region(unidecode(req[0]),req[1][0],10,draw=1)
        
        
        
            
