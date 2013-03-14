starcluster_hadoop_plugin
=========================

This plugin configures and runs Hadoop using MIT's StarCluster software tools.  Once StarCluster is finished creating its cluster of virtual machines, it configures the cluster for Hadoop and then starts the Hadoop daemons.

The plugin is a modified and updated version of the Hadoop plugin provided with the StarCluster version 0.93 distribution.  While the distributed plugin is limited to Hadoop version 0.20, this plugin supports Hadoop version 1.0.4 and should be general enough to support subsequent versions of Hadoop.

It features more configuration options than the distributed plugin. These options can be set in the StarCluster config file.

The Hadoop software is assumed to be alreadly installed on the virtual machines.  A user-data file is included in the repo for installing hadoop on Ubuntu server versions 12.04 and 12.10 and creating a compliant virtual machine that can be burned into an AMI image.  Although StarCluster expects NFS to be installed on its virtual machines, Hadoop runs fine without it despite StarCluster's error messages.

Hadoop requires one user to be the one hadoop 'master' user.  The master user starts the Hadoop daemons and is authorized to do administration of the Hadoop distributed file system.  This user needs passwordless access through ssh to all the other nodes in order to do this.  This functionality is setup by the include user-data file.  The plugin has a setting called HADOOP_USER that names the hadoop user.  By default it is set to user 'hadoop'.  If the user name changes the setting much be changed as well.

This plugin is not dependent on the StarCluster 'cluster user' therefore that user can be used without restriction.

Oddly enough I found it easier to run Hadoop on Amazon's EC2 instances as a cluster than running it in standalone mode on one machine.  In addition StarCluster makes it very easy to start a cluster of machines.  For example it configures each machine's /etc/hosts file so they can talk to one another without having to set it up manually.

An example starcluster 'config' file is shown below:

```ini
[global]
DEFAULT_TEMPLATE=hadoop_cluster

[aws info]
AWS_ACCESS_KEY_ID = 99999999999999999999
AWS_SECRET_ACCESS_KEY = 9999999999999999999999999999999999999999
AWS_USER_ID = 999999999999

[key mykey]
KEY_LOCATION=~/.ssh/mykey.pem

[cluster hadoop_cluster]
KEYNAME = mykey
VOLUMES = climate
PLUGINS = hadoop_plugin
NODE_IMAGE_ID = ami-5e7eec37
CLUSTER_USER = george
CLUSTER_SIZE = 2
NODE_INSTANCE_TYPE = t1.micro

[plugin hadoop_plugin]
SETUP_CLASS = hadoop_plugin.Hadoop
MAP_TASKS_MAX = 1

# Daily Global Weather Measurements
[volume climate]
VOLUME_ID = vol-99999999
MOUNT_PATH = /home/climate
```

The cluster user was used to run hadoop job from, leaving the hadoop user for superuser purposes.  The 'volume climate' section was used to mount Amazon's climate public data set.

As the config file shows, hadoop can be run across micro instances on Amazon EC2.  However set the number of maximum map tasks to one because system memory is very limited.  Micro instances let you experiment using Amazon's free tier.  

Moving to the m1.small instance types, the number of maximum map tasks can be raised to two, which is the default.  In addition, ephemeral storage is provided free for m1.small instances.  This storage can be used as part of HDFS.  The plugin assumes ephemeral storage is mounted on /mnt.  It should be noted that any user created AMIs must be configured to use ephemeral storage.  The easiest way to do this is through the AWS console interface when burning the AMI.

The included user-data file will also install the software package 'dumbo'.   Dumbo abstracts a lot of the complexity of writing and running map reduce jobs.  To give an sample session with Hadoop I will use dumbo as an example.

First start the cluster:

```bash
$ starcluster start ansonia
```

Wait till starcluster finishes then download the US Constitution and copy it into HDFS:

```bash
$ starcluster sshmaster ansonia -u george 'hadoop fs -mkdir input'
$ starcluster sshmaster ansonia -u george 'wget www.usconstitution.net/const.txt'
$ starcluster sshmaster ansonia -u george 'hadoop fs -put const.txt input'
$ starcluster sshmaster ansonia -u george 'hadoop fs -lsr'
```

Copy the word.py dumbo script into the master:

```bash
$ cat word.py
```

```python
def mapper (key, value):
    for word in value.split(): yield word, 1
def reducer (key, values):
    yield key, sum(values)
```

```bash
$ starcluster put ansonia -u george word.py .
```

Now run a word count against the constitution.  Note, the '-hadoop yes' option is configured in /etc/dumbo.conf and tells dumbo to use hadoop to run the script.

```bash
$ starcluster sshmaster ansonia -u george 'dumbo start word.py -input input -output output -hadoop yes'
$ starcluster sshmaster ansonia -u george 'hadoop fs -lsr'
$ starcluster sshmaster ansonia -u george 'hadoop -cat output/part*'
```

Shut down the cluster:

```bash
$ starcluster terminate ansonia
```




