#######################################################################
# DB Settings
# Just put your settings here.
########################################################################
db_name="mconf_chat_portal"
db_user="mconf_chat"
db_pass="my-password"
db_host="localhost"
db_select_users_tokens="SELECT users.username, chat_tokens.token FROM users AS users INNER JOIN chat_tokens AS chat_tokens ON users.id = chat_tokens.user_id WHERE users.username = '%s';"
domain_suffix="@my-server.com"

########################################################################
# Setup
########################################################################
import sys, logging, struct, hashlib, MySQLdb, requests

from struct import *
from xml.dom.minidom import parseString

sys.stderr = open('/var/log/ejabberd/extauth_err.log', 'a')

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    filename='/var/log/ejabberd/extauth.log',
                    filemode='a')

try:
        database=MySQLdb.connect(host=db_host, port=3306, user=db_user, passwd=db_pass, db=db_name)
        # without the line below we might get always the same data even though it was changed in the
        # database (e.g. a user password changed)
        # More at: http://stackoverflow.com/questions/5943418/chronic-stale-results-using-mysqldb-in-python
        database.autocommit(True)
except:
        logging.debug("Unable to initialize database, check settings!")
dbcur=database.cursor()
logging.info('extauth script started, waiting for ejabberd requests')
class EjabberdInputError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

########################################################################
# Declarations
########################################################################
def db_connect():
        try:
                database = MySQLdb.connect(host=db_host, port=3306, user=db_user, passwd=db_pass, db=db_name)
        except:
                logging.debug("Unable to initialize database, check settings!")

def ejabberd_in():
                logging.debug("trying to read 2 bytes from ejabberd:")
                try:
                        input_length = sys.stdin.read(2)
                except IOError:
                        logging.debug("ioerror")
                if len(input_length) is not 2:
                        logging.debug("ejabberd sent us wrong things!")
                        raise EjabberdInputError('Wrong input from ejabberd!')
                logging.debug('got 2 bytes via stdin: %s'%input_length)
                (size,) = unpack('>h', input_length)
                logging.debug('size of data: %i'%size)
                income=sys.stdin.read(size).split(':')
                logging.debug("incoming data: %s"%income)
                return income

def ejabberd_out(bool):
                logging.debug("Ejabberd gets: %s" % bool)
                token = genanswer(bool)
                logging.debug("sent bytes: %#x %#x %#x %#x" % (ord(token[0]), ord(token[1]), ord(token[2]), ord(token[3])))
                sys.stdout.write(token)
                sys.stdout.flush()

def genanswer(bool):
                answer = 0
                if bool:
                        answer = 1
                token = pack('>hh', 2, answer)
                return token

def db_entry(in_user):
        sql = db_select_users_tokens % (in_user)
        logging.debug("Selecting users and tokens with: "+sql)
        dbcur.execute(sql)
        found = dbcur.fetchall()
        logging.debug("Select found: {}".format(found))
        return found

def isuser(in_user, in_host):
        logging.debug("User unescaped: "+in_user)
        data_set=db_entry(in_user)
        out=False

        if data_set==None:
                logging.debug("Wrong username: %s"%(in_user))
                return out

        for data in data_set:
                logging.debug("Data: "+data[0]+domain_suffix)
                if in_user+"@"+in_host==data[0]+domain_suffix:
                        out=True
                        break
        return out

def auth(in_user, in_host, password):
        try:
                data_set=db_entry(in_user)
        except Exception, err:
                logging.debug("Got exception: {}".format(err))
                try:
                        db_connect()
                except:
                        logging.debug("Database fail")
                        return False
        out=False

        if data_set==None:
                logging.debug("Wrong username: %s"%(in_user))
                return out

        for data in data_set:
                if in_user+"@"+in_host==data[0]+domain_suffix:
                        if password==data[1]:
                                return True
                        else:
                                logging.debug("Wrong password for user: %s"%(in_user))
        return out

def log_result(op, in_user, bool):
        if bool:
                logging.info("%s successful for %s"%(op, in_user))
        else:
                logging.info("%s unsuccessful for %s"%(op, in_user))

########################################################################
# Main Loop
########################################################################
while True:
        logging.debug("start of infinite loop")
        try:
                ejab_request = ejabberd_in()
        except EjabberdInputError, inst:
                logging.info("Exception occured: %s", inst)
                break
        logging.debug('operation: %s'%(ejab_request[0]))
        op_result = False
        ejab_request[1] = ejab_request[1].replace("\\40","@")

        logging.debug("User: "+ejab_request[1])
        if ejab_request[0] == "auth":
                op_result = auth(ejab_request[1], ejab_request[2], ejab_request[3])
                ejabberd_out(op_result)
                log_result(ejab_request[0], ejab_request[1], op_result)
        elif ejab_request[0] == "isuser":
                op_result = isuser(ejab_request[1], ejab_request[2])
                ejabberd_out(op_result)
                log_result(ejab_request[0], ejab_request[1], op_result)

logging.debug("end of infinite loop")
logging.info('extauth script terminating')
database.close()
