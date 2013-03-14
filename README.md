starcluster_hadoop_plugin
=========================

This plugin configures and runs Hadoop using MIT's StarCluster software tools.  Once StarCluster is finished creating its cluster of virtual machines, this plugin configures the cluster for Hadoop and then starts the Hadoop daemons.

The plugin is a modified and updated version of the Hadoop plugin provided with the StarCluster version 0.93 distribution.  While the distributed plugin is limited to Hadoop version 0.20, this plugin supports Hadoop version 1.0.4 and should be general enough to support subsequent versions of Hadoop.

It features more configuration options than the distributed plugin. These options can be set in the StarCluster 'config' file.

The Hadoop software is assumed to be alreadly installed on the virtual machines.  A 'user-data' file is included in the repo for installing Hadoop on Ubuntu server versions 12.04 and 12.10 and for creating a compliant virtual machine.  This virtual machine can be burned into an AMI image and used as the node image id for the cluster.  Although StarCluster expects NFS to be installed on its virtual machines, Hadoop runs fine without it despite StarCluster's error messages.

If you are familiar with Hadoop, Hadoop requires one user to be the Hadoop master superuser.  The master superuser is the user who starts the Hadoop daemons and who is authorized to do administration of the Hadoop distributed file system.  This user requires passwordless access through ssh to all the other nodes in order to do this.  This functionality is configured by the included 'user-data' file.  

The plugin has a setting called HADOOP_USER that sets the name of this Hadoop superuser.  By default it is set to the user 'hadoop'.  If the user name changes this setting much be changed as well.

This plugin was intentionally designed not to be dependent on the StarCluster cluster user.  Because of that the cluster user can be used without restriction, for example as a general user of the Hadoop cluster.

An example StarCluster 'config' file is shown below:

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

As the config file shows, Hadoop can be run across Amazon EC2 micro instances.  If micro instances are used set the number of maximum map tasks to one since system memory is very limited on these instance types.

Moving to the m1.small instance types, the number of maximum map tasks can be raised from one to two, which is the default.  In addition, ephemeral storage is provided free by Amazon for m1.small instances.  This storage can be used by the cluster as part of HDFS.  For this to happen ephemeral storage must be mounted on /mnt since this is where the plugin assumes ephemeral storage is mounted.  It should also be noted that any user created AMI images must be explicitly configured to use ephemeral storage.  The easiest way to do this is through the AWS console interface by selecting the instance storage tab when creating an AMI.

The included 'user-data' file will also install the software package 'dumbo'.   Dumbo abstracts much of the complexity of writing and running map reduce jobs.  To give an sample session with or StarCluster with Hadoop I will use dumbo as an example.

First start the cluster:

```bash
$ starcluster start ansonia
```

Wait until StarCluster finishes then download the US Constitution and copy it into HDFS:

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
if __name__ == "__main__":
    import dumbo
    dumbo.run(mapper, reducer, combiner=reducer)
```

```bash
$ starcluster put ansonia -u george word.py .
```

Now run a word count against the constitution.  Note, the '-hadoop yes' option is configured in /etc/dumbo.conf and tells dumbo to use hadoop to run the script.

```bash
$ starcluster sshmaster ansonia -u george 'dumbo start word.py -input input -output output -hadoop yes'
$ starcluster sshmaster ansonia -u george 'hadoop fs -lsr'
$ starcluster sshmaster ansonia -u george 'hadoop fs -cat output/part*'
```

Shut down the cluster:

```bash
$ starcluster terminate ansonia
```




