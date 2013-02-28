import posixpath

from starcluster import threadpool
from starcluster import clustersetup
from starcluster.logger import log

core_site_templ = """\
<?xml version="1.0"?>
<configuration>
<property>
  <name>fs.default.name</name>
  <value>hdfs://master/</value>
  <final>true</final>
</property>
</configuration>
"""

hdfs_site_templ = """\
<?xml version="1.0"?>
<configuration>
<property>
  <name>dfs.replication</name>
  <value>%(dfs_replication)d</value>
  <final>true</final>
</property>

<property>
  <name>dfs.data.dir</name>
  <value>%(dfs_data_dir)s</value>
  <final>true</final>
</property>

<property>
  <name>dfs.name.dir</name>
  <value>%(dfs_name_dir)s</value>
  <final>true</final>
</property>

<property>
  <name>dfs.hosts.exclude</name>
  <value>%(dfs_hosts_exclude)s</value>
  <final>true</final>
</property>

<property>
  <name>dfs.datanode.du.reserved</name>
  <value>%(dfs_du_reserved)d</value>
  <final>true</final>
</property>
</configuration>
"""

mapred_site_templ = """\
<?xml version="1.0"?>
<configuration>
<property>
  <name>mapred.job.tracker</name>
  <value>master:8021</value>
</property>

<property>
  <name>mapred.local.dir</name>
  <value>%(mapred_local_dir)s</value>
  <final>true</final>
</property>

<property>
  <name>mapred.system.dir</name>
  <value>%(mapred_system_dir)s</value>
  <final>true</final>
</property>

<property>
  <name>mapreduce.jobtracker.staging.root.dir</name>
  <value>%(mapred_staging_root_dir)s</value>
  <final>true</final>
</property>

<property>
  <name>mapred.tasktracker.map.tasks.maximum</name>
  <value>%(mapred_map_tasks_maximum)d</value>
  <final>true</final>
</property>

<property>
  <name>mapred.tasktracker.reduce.tasks.maximum</name>
  <value>%(mapred_reduce_tasks_maximum)d</value>
  <final>true</final>
</property>

<property>
  <name>mapred.reduce.tasks</name>
  <value>%(mapred_reduce_tasks)d</value>
  <final>true</final>
</property>

<property>
  <name>mapred.child.java.opts</name>
  <value>%(mapred_child_java_opts)s</value>
  <!-- Not marked as final so jobs can include JVM debugging options -->
</property>
</configuration>
"""


# recommmended maximum tasks per node
# type      maps reduces 
# ----------------------
# m1.small    2    1
# c1.medium   4    2
# m1.large    4    2
# m1.xlarge   8    4
# c1.xlarge   8    4

class Hadoop(clustersetup.ClusterSetup):
    """
    Configures Hadoop using StarCluster
    """

    def __init__(self, 
                 hadoop_user='hadoop',
                 map_tasks_max=2, 
                 reduce_tasks_max=1, 
                 reduce_tasks_factor=1.75, 
                 dfs_replication=None,
                 dfs_du_reserved=2**30,
                 mapred_child_java_opts='-Xmx512m'):

        self.hadoop_user = hadoop_user
        self.hadoop_pid_dir = '/var/run/hadoop'
        self.hadoop_log_dir = '/var/log/hadoop'
        self.hadoop_conf = '/etc/hadoop'
        self.dfs_hosts_exclude = '/etc/hadoop/excludes'

        self.dfs_dir = '/mnt/hadoop'
        self.dfs_data_dir = '/mnt/hadoop/dfs/data'
        self.dfs_name_dir = '/mnt/hadoop/dfs/name'
        self.dfs_du_reserved = float(dfs_du_reserved)
        self.dfs_replication = dfs_replication

        self.mapred_local_dir = '/mnt/hadoop/mapred/local'
        self.mapred_system_dir = '/user/${user.name}/.staging'
        self.mapred_staging_root_dir = '/user'
        self.mapred_map_tasks_maximum = float(map_tasks_max)
        self.mapred_reduce_tasks_maximum = float(reduce_tasks_max) 
        self.mapred_reduce_tasks_factor = float(reduce_tasks_factor)
        self.mapred_child_java_opts = mapred_child_java_opts

        self._pool = None

    @property
    def pool(self):
        if self._pool is None:
            self._pool = threadpool.get_thread_pool(20, disable_threads=False)
        return self._pool

    def _configure_mapreduce_site(self, node, cfg):
        mapred_site_xml = posixpath.join(self.hadoop_conf, 'mapred-site.xml')
        mapred_site = node.ssh.remote_file(mapred_site_xml)
        mapred_site.write(mapred_site_templ % cfg)
        mapred_site.close()

    def _configure_core(self, node, cfg):
        core_site_xml = posixpath.join(self.hadoop_conf, 'core-site.xml')
        core_site = node.ssh.remote_file(core_site_xml)
        core_site.write(core_site_templ % cfg)
        core_site.close()

    def _configure_hdfs_site(self, node, cfg):
        hdfs_site_xml = posixpath.join(self.hadoop_conf, 'hdfs-site.xml')
        hdfs_site = node.ssh.remote_file(hdfs_site_xml)
        hdfs_site.write(hdfs_site_templ % cfg)
        hdfs_site.close()

    def _configure_masters(self, node, master):
        masters_file = posixpath.join(self.hadoop_conf, 'masters')
        masters_file = node.ssh.remote_file(masters_file)
        masters_file.write(master.alias)
        masters_file.close()

    def _configure_slaves(self, node, node_aliases):
        slaves_file = posixpath.join(self.hadoop_conf, 'slaves')
        slaves_file = node.ssh.remote_file(slaves_file)
        slaves_file.write('\n'.join(node_aliases[1:]))
        slaves_file.close()

    def _configure_hosts_exclude(self, node):
        mapred_site = node.ssh.remote_file(self.dfs_hosts_exclude)
        mapred_site.write("")
        mapred_site.close()

    def _setup_hadoop_dir(self, node, path, user, group, permission="775"):
        if not node.ssh.isdir(path):
            node.ssh.mkdir(path)
        node.ssh.execute("chown -R %s:%s %s" % (user, group, path))
        node.ssh.execute("chmod -R %s %s" % (permission, path))

    def _setup_hdfs(self, node, user):
        self._setup_hadoop_dir(node, self.dfs_dir, user, user)
        self._setup_hadoop_dir(node, self.hadoop_pid_dir, user, user)
        self._setup_hadoop_dir(node, self.hadoop_log_dir, user, user)

    def _setup_dumbo(self, node):
        f = node.ssh.remote_file('/etc/dumbo.conf')
        f.write('[common]\n');
        f.write('hadooplib: /usr/share/hadoop/contrib/streaming\n');
        f.write('outputformat: text\n');
        f.write('overwrite: yes\n');
        f.write('[hadoops]\n');
        f.write('yes: /usr\n');
        f.close()

    def _configure_hadoop(self, master, nodes, user):
        log.info("Configuring Hadoop...")

        node_aliases = map(lambda n: n.alias, nodes)
        slaves = len(nodes) - 1

        if self.dfs_replication != None:
            self.dfs_replication = float(self.dfs_replication)
        else:
            self.dfs_replication = 2
            if slaves >= 8: self.dfs_replication = 3
        log.info("Using a HDFS replication factor of %d..." % self.dfs_replication)

        mapred_reduce_tasks = self.mapred_reduce_tasks_maximum * slaves
        mapred_reduce_tasks *= self.mapred_reduce_tasks_factor
        mapred_reduce_tasks += .5
        log.info("Using %d reduce tasks for %d slave(s)..." % 
                 (mapred_reduce_tasks, slaves))

        cfg = { 
            'dfs_data_dir': self.dfs_data_dir,
            'dfs_name_dir': self.dfs_name_dir,
            'dfs_du_reserved': self.dfs_du_reserved,
            'dfs_hosts_exclude': self.dfs_hosts_exclude,
            'dfs_replication': self.dfs_replication,
            'mapred_local_dir': self.mapred_local_dir,
            'mapred_system_dir': self.mapred_system_dir,
            'mapred_map_tasks_maximum': self.mapred_map_tasks_maximum,
            'mapred_reduce_tasks_maximum': self.mapred_reduce_tasks_maximum,
            'mapred_child_java_opts': self.mapred_child_java_opts,
            'mapred_staging_root_dir': self.mapred_staging_root_dir,
            'mapred_reduce_tasks': mapred_reduce_tasks
            }

        log.info("Configuring MapReduce Site...")
        for node in nodes:
            self.pool.simple_job(self._configure_mapreduce_site, (node, cfg), 
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))
        log.info("Configuring Core Site...")
        for node in nodes:
            self.pool.simple_job(self._configure_core, (node, cfg), 
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))
        log.info("Configuring HDFS Site...")
        for node in nodes:
            self.pool.simple_job(self._configure_hdfs_site, (node, cfg), 
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))
        log.info("Configuring masters file...")
        for node in nodes:
            self.pool.simple_job(self._configure_masters, (node, master), 
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))
        log.info("Configuring slaves file...")
        for node in nodes:
            self.pool.simple_job(self._configure_slaves, (node, node_aliases), 
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))
        log.info("Configuring host excludes file...")
        for node in nodes:
            self.pool.simple_job(self._configure_hosts_exclude, node, jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))
        log.info("Configuring local directories...")
        for node in nodes:
            self.pool.simple_job(self._setup_hdfs, (node, user), 
                                 jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))
        log.info("Configuring dumbo...")
        for node in nodes:
            self.pool.simple_job(self._setup_dumbo, (node,), jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))

    def _start_hadoop(self, master, nodes, hadoop_user, user):
        log.info("Formatting namenode...")
        master.ssh.execute("su %s -c 'hadoop namenode -format'" % hadoop_user)
        log.info("Starting HDFS...")
        master.ssh.execute("su %s -c 'start-dfs.sh'" % hadoop_user)
        log.info("Starting mapred...")
        master.ssh.execute("su %s -c 'start-mapred.sh'" % hadoop_user)
        log.info("Creating the HDFS home directory of user %s..." % user)
        master.ssh.execute("su %s -c 'hadoop fs -mkdir /user/%s'" % (hadoop_user, user))
        master.ssh.execute("su %s -c 'hadoop fs -chown %s /user/%s'" % (hadoop_user, user, user))

    def _open_ports(self, master):
        ports = [50070, 50030]
        ec2 = master.ec2
        for group in master.cluster_groups:
            for port in ports:
                has_perm = ec2.has_permission(group, 'tcp', port, port, '0.0.0.0/0')
                if not has_perm:
                    group.authorize('tcp', port, port, '0.0.0.0/0')

    def run(self, nodes, master, user, user_shell, volumes):
        try:
            self._configure_hadoop(master, nodes, self.hadoop_user)
            self._start_hadoop(master, nodes, self.hadoop_user, user)
            self._open_ports(master)
            log.info("Job tracker status: http://%s:50030" % master.dns_name)
            log.info("Namenode status: http://%s:50070" % master.dns_name)
        finally:
            self.pool.shutdown()









