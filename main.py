import os
import fnmatch
import logging
import requests
from ftplib import FTP
from configparser import ConfigParser
from datetime import datetime, timedelta


##########################Config reader###########################################
def get_conf(section, filename='ftp.ini'):
    parser = ConfigParser()
    parser.read(filename)
    conf = {}
    try:
        for item in parser.items(section):
            conf[item[0]] = item[1]
    except Exception as err:
        logging.error(str(err))
        return
    return conf


#########################HTTP(S) to file dowloader###################################
def dl_http(url, file):
    norad_cfg = get_conf(section='norad')
    norad_cred = {'identity': norad_cfg['user'], 'password': norad_cfg['password']}
    headers = {'User-Agent': 'Mozilla/5.0'}
    login_norad_url = 'https://www.space-track.org/ajaxauth/login'
    local_cfg = get_conf(section='local')
    cat_file = local_cfg['cat']
    glo_file = local_cfg['glo']
    if file == cat_file:
        with requests.Session() as session:
            session.post(login_norad_url, data=norad_cred)
            r = session.get(url)
    else:
        r = requests.get(url, headers=headers)
    if r.ok:
        if file == glo_file:
            with open(file, 'wt') as outfile:
                outfile.write(r.text)
        else:
            with open(file, 'wb') as outfile:
                outfile.write(r.content)
    else:
        logging.error('HTTP status : {0} ({1}) in {2}'.format(r.status_code, r.reason, r.url))


#############################CPF ftp downloader###################################
def cpf_dl():
    ftp_cfg = get_conf(section='ftp')
    local_cfg = get_conf(section='local')
    local_dir = local_cfg['cpf']
    srv = ftp_cfg['server']
    path = ftp_cfg['path']
    user = ftp_cfg['user']
    password = ftp_cfg['password']
    best_date_stamp = 0
    best_cpf = ''
    old_cpf = ''
    ftp = FTP(srv)
    logging.debug('Login to FTP...')
    try:
        ftp.login(user, password)
        logging.debug('Login succesfull')
        ftp.cwd(path)
        logging.debug('Source directory changed')
        remote_file_list = ftp.nlst()
        logging.debug('Source directory read')
    except Exception as err:
        logging.error(str(err))
        return
    local_file_list = os.listdir(local_dir)
    splt_filename = remote_file_list[0].split('_')
    cur_sat_name = splt_filename[0]
    for filename in remote_file_list:
        splt_filename = filename.split('_')
        try:
            sat_name = splt_filename[0]
            date = splt_filename[2]
            ext_tmp = splt_filename[3]
            date_stamp = int(date + ext_tmp[0:4])
        except Exception as err:
            logging.error('Filename [' + filename + '] is bad ' + str(err))
            continue
        if cur_sat_name != sat_name:
            full_path = os.path.join(local_dir,  best_cpf)
            logging.debug('Best file : ' + best_cpf)
            if not os.path.isfile(full_path):
                for old_local_file in local_file_list:
                    if fnmatch.fnmatch(old_local_file, old_cpf):
                        logging.debug('Deleting old file ' + old_local_file)
                        os.remove(os.path.join(local_dir, old_local_file))
                    else:
                        continue
                logging.debug('Download file ' + best_cpf + ' ...')
                with open(full_path, 'wb') as local_file:
                    ftp.retrbinary('RETR ' + best_cpf, local_file.write, 1024)
                logging.debug('Ok.')

            else:
                logging.debug('Exist, skipped.')
                pass
            best_date_stamp = 0
        cur_sat_name = sat_name
        if date_stamp > best_date_stamp:
            best_date_stamp = date_stamp
            best_cpf = filename
            old_cpf = sat_name + '_*.*'
    ftp.close()
    logging.debug('FTP close... OK')


#########################EOP http downloader######################################
def eop_dl():
    local_cfg = get_conf(section='local')
    eop_path = local_cfg['eop']
    url = 'http://celestrak.org/SpaceData/EOP-Last5Years.txt'
    eop_old = eop_path + 'q.txt'
    eop_new = eop_path + 'q_new.txt'
    if os.path.isfile(eop_old):
        with open(eop_old, 'r') as file:
            for string in file:
                string_split = string.split(' ')
                if string_split[0] == 'UPDATED':
                    old_date = datetime.strptime(' '.join(string_split[1:5]), '%Y %b %d %H:%M:%S')
                    logging.debug('Current EOP date: ' + str(old_date))
                    break
        dt_now = datetime.now()
        if dt_now > old_date + timedelta(days=1):
            logging.debug('Downloading EOP...')
            dl_http(url, eop_new)
            with open(eop_new, 'r') as file:
                for string in file:
                    string_split = string.split(' ')
                    if string_split[0] == 'UPDATED':
                        new_date = datetime.strptime(' '.join(string_split[1:5]), '%Y %b %d %H:%M:%S')
                        logging.debug('New EOP date: ' + str(new_date))
                        break
            if new_date > old_date:
                os.remove(eop_old)
                os.rename(eop_new, eop_old)
                logging.debug('EOP updated')
            else:
                logging.debug('EOP already updated')
                os.remove(eop_new)
        else:
            logging.debug('EOP already updated')
    else:
        logging.debug('Downloading EOP first time...')
        dl_http(url, eop_old)


##################Glonass bulletin https downlader###############################
def glo_dl():
    local_cfg = get_conf(section='local')
    glo_file = local_cfg['glo']
    # eph_file = local_cfg['eph']
    y = datetime.now().strftime('%Y')
    m = datetime.now().strftime('%m')
    d = datetime.now().strftime('%d')
    h = datetime.now().strftime('%H')
    url = 'https://glonass-iac.ru/upload/monitoring/cus/{0}/{1}{2}ru.txt'.format(y, m, d)
    # url_eph = 'https://glonass-iac.ru/glonass/ephemeris/'
    # dl_http(url_eph, eph_file)
    if int(h) > 12:
        dl_http(url, glo_file)
    else:
        logging.debug('Too early to download the bulletin')


##################NORAD catalog downloader#######################################
def cat_dl():
    local_cfg = get_conf(section='local')
    cat_file = local_cfg['cat']
    url = 'https://www.space-track.org/basicspacedata/query/class/' \
          'gp/EPOCH/%3Enow-30/orderby/NORAD_CAT_ID,EPOCH/format/3le'
    dl_http(url, cat_file)


##################################################################################
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, filename='sync.log',
                        format='[%(asctime)s] %(levelname)s: %(message)s')
    logging.debug('Lets do it!')
    try:
        # eop_dl()
        # glo_dl()
        # cat_dl()
        cpf_dl()
    except Exception as error:
        logging.error(str(error))
    finally:
        logging.debug('I did it!')
        logging.debug('Sleeping for 1 hour...')
