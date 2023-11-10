import logging
import downloader as dl

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, filename='sync.log',
                        format='[%(asctime)s] %(levelname)s: %(message)s')
    logging.debug('Lets do it!')
    try:
        dl.eop_dl()
        dl.glo_dl()
        dl.cat_dl()
        dl.cpf_dl()
    except Exception as error:
        logging.error(str(error))
    finally:
        logging.debug('I did it!')
        logging.debug('Sleeping for 1 hour...')
