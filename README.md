Mconf Chat Server
=================

This repository holds the files to configure the server component for the chat applications on Mconf.
The server used is the open source XMPP server [ejabberd](http://www.ejabberd.im/).

The server is integrated with a web application that will be used to authenticate the users.
An example of a web application can be found at [mconf-chat-auth-example](https://github.com/mconf/mconf-chat-auth-example) and it can also be used with [Mconf-Web](https://github.com/mconf/mconf-web).


## Installation

Install `ejabberd` and some other packages needed. Python and the lib `requests` are used in the external authentication script.

```bash
sudo apt-get install ejabberd python-mysqldb python-pip
sudo pip install requests
```

Install the module `mod_admin_extra` (additional commands for ejabberd). Needed to use VCards.

```bash
sudo wget https://github.com/mconf/mconf-chat-server/raw/master/mod_admin_extra.beam -O /usr/lib/ejabberd/ebin/mod_admin_extra.beam
```

To start/stop it use:

```bash
sudo /etc/init.d/ejabberd start
sudo /etc/init.d/ejabberd stop
```

### If using a firewall

The ports 5280 (web administration) and 5222 (client communication) should be open.

If you're using `iptables`, add the following to `/etc/default/firewall`:

```bash
iptables -A INPUT -p tcp --dport 5280 -j ACCEPT
iptables -A INPUT -p tcp --dport 5222 -j ACCEPT
```


## Configuration

Edit `/etc/ejabberd/ejabberd.cfg` (replace `$DOMAIN$` by your domain, e.g. mconf.org):

```
%% Admin user
{acl, admin, {user, "admin", "$DOMAIN$"}}.
{acl, adminextraresource, {resource, "modadminextraf8x,31ad"}}.
{access, vcard_set, [
    {allow, adminextraresource},
    {deny, all}]
}.

%% Hostname
{hosts, ["$DOMAIN$"]}.

...

%%
%% Modules enabled in all ejabberd virtual hosts.
%%
{modules,
 [
  {mod_http_bind, []},       # Add this line
  {mod_adhoc,    []},

  ...

  # The lines below already exist, replace them.
  {mod_admin_extra, [ {module_resource, "modadminextraf8x,31ad"} ]},
  {mod_vcard,       [ {access_set, vcard_set} ]},
]}.

...

%% auth_method: Method used to authenticate the users.
%% The default method is the internal.
%% If you want to use a different method,
%% comment this line and enable the correct ones.
%%
%% {auth_method, internal}. # Comment

%%
%% Authentication using external script
%% Make sure the script is executable by ejabberd.
%%
# Uncomment and chage to:
{auth_method, external}.
{extauth_program, "python /var/lib/ejabberd/JabberAuth.py"}.
```


## External authentication

We'll add a script to `ejabberd` to authenticate the users using the web application's database.

Create a new user in the database for `ejabberd`. This user should have access to the target database.
Access MySQL monitor (`mysql -u root -p`) and:

```bash
CREATE USER 'mconf_xmpp'@'localhost' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON mconf_production.users TO "mconf_xmpp"@"localhost" IDENTIFIED BY "password";
FLUSH PRIVILEGES;
```

<font color=red>TODO: We are currently using the same db user the web application uses. The commands above should also be tested.</font>

Then get the script:

```bash
sudo wget https://github.com/mconf/mconf-chat-server/raw/master/JabberAuth.py -O /var/lib/ejabberd/JabberAuth.py
sudo chown ejabberd:ejabberd /var/lib/ejabberd/JabberAuth.py
```

And configure it:

```
##########################################################
#DB Settings
#Just put your settings here.
##########################################################
db_name="mconf_production"
db_user="mconf"
db_pass="my-password"
db_host="my-server.com"
db_table="users"
db_username_field="login"
db_password_field="crypted_password"
db_salt_field="salt"
domain_suffix="@my-server.com"
auth_url="http://my-server.com/xmpp/me"
```

## Log and configuration files

The log files can be found at:

```bash
/var/log/ejabberd/ejabberd.log     # ejabberd default log
/var/log/ejabberd/extauth.log      # authentication log
/var/log/ejabberd/extauth_err.log  # authentication errors
```

The configuration clients can be found at:

```bash
/etc/ejabberd/ejabberd.cfg         # ejabberd's configuration file
/var/lib/ejabberd/JabberAuth.py    # external authentication script
```

<font color=red>TODO: The server with the MySQL database should have it configured to allow external connections. Add instructions on how to do it and how to test if external connections are allowed (everything's already in the "Development" section below.).</font>


## Enabling chat history

Stop ejabberd:

```bash
sudo /etc/init.d/ejabberd stop
```

Install the modules `mod_archive_odbc`, `mysql`, `mysql_auth`, `mysql_conn` and `mysql_recv`.

```bash
sudo wget https://github.com/mconf/mconf-chat-server/raw/master/mod_archive_odbc.beam -O /usr/lib/ejabberd/ebin/mod_archive_odbc.beam
sudo wget https://github.com/mconf/mconf-chat-server/raw/master/mysql.beam -O /usr/lib/ejabberd/ebin/mysql.beam
sudo wget https://github.com/mconf/mconf-chat-server/raw/master/mysql_auth.beam -O /usr/lib/ejabberd/ebin/mysql_auth.beam
sudo wget https://github.com/mconf/mconf-chat-server/raw/master/mysql_conn.beam -O /usr/lib/ejabberd/ebin/mysql_conn.beam
sudo wget https://github.com/mconf/mconf-chat-server/raw/master/mysql_recv.beam -O /usr/lib/ejabberd/ebin/mysql_recv.beam
```

Then get the script and execute it (replace `$USER$` by your MySQL user).

```bash
sudo wget https://github.com/mconf/mconf-chat-server/raw/master/mod_archive_odbc_mysql.sql -O /tmp/mod_archive_odbc_mysql.sql
mysql -u $USER$ -p < /tmp/mod_archive_odbc_mysql.sql
```

Now create a new user in MySQL to access the ejabberd database:

```bash
CREATE USER 'ejabberd_log'@'localhost' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON ejabberd.* TO "ejabberd_log"@"localhost" IDENTIFIED BY "password";
FLUSH PRIVILEGES;
```

Edit /etc/ejabberd/ejabberd.cfg:

```
%%
%% MySQL server:
%% Uncomment and change to:
{odbc_server, {mysql, "localhost", "ejabberd", "ejabberd_log", "password"}}.
%%

...

{mod_vcard,       [ {access_set, vcard_set} ]},
{mod_version,  []},     # Put a comma on the end of this line
{mod_archive_odbc, [{database_type, "mysql"},
                    {default_auto_save, true },
                    {enforce_default_auto_save, false },
                    {default_expire, infinity },
                    {enforce_min_expire, 0 },
                    {enforce_max_expire, infinity },
                    {replication_expire, 31536000 },
                    {session_duration, 1800 },
                    {wipeout_interval, 86400}]}
```

Start ejabberd:

```bash
sudo /etc/init.d/ejabberd start
```


# Development

You need to allow external connections to your MySQL db: edit `/etc/mysql/my.cnf` and make the section `[mysqld]` like this:

```
[mysqld]
bind-address    = 0.0.0.0
port            = 3306
user              = mysql
pid-file        = /var/run/mysqld/mysqld.pid
socket          = /var/run/mysqld/mysqld.sock
basedir         = /usr
datadir         = /var/lib/mysql
tmpdir          = /tmp
language        = /usr/share/mysql/English
# skip-networking
# skip-external-locking
```

Restart MySQL after changing its configurations

```bash
sudo service mysql restart
```

The db user should be able to access the database even from another host:

```sql
GRANT ALL PRIVILEGES ON mconf_production.* TO 'mconf'@'%' IDENTIFIED BY '<password>' WITH GRANT OPTION;
FLUSH PRIVILEGES;
```

To test it, go to your chat server and run:

```bash
mysql -h <domain of your mysql server> -u mconf -p
```
