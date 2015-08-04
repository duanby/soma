SOMA data analysis manager
--------------------------
5. Run the SOMA object manager:

    ```
    $ rosrun soma_data_analysis object.py 
    ```
input:
for request waypoint, input one waypoint in the form: "WayPoint42"

for operation, input one of the following operations:
    "box"    :  generate and display bounding boxes given one label and one instance
    "cloud"  :  display the point cloud of one label and one instance
    "single" :  compute the distribution of the movement of a single object given a list of instances, one label and one specific object and display the region where this object is movable.
    "tv_spatial" : compute the possibility of a tv being on a table given a list of instances.
    "chair_spatial" : compute the possibility of a chair being near a table given a list of instances.

for request instances, input instances corresponding to the operation in the form: [0] or [0,1,2,5]

for request label, input the number representing the label: (range from 0 to 10)
    label_type=["prop","wall","cabinet","ceiling","chair/sofa", "window", "floor","monitor/tv","person","shelf", "table"]

for specific object(especially for mission 'single') : input a number refering to an object in the first instance of the querying list.


