# Build Version: #VERSION
# Test Version - DO NOT DEPLOY. NOT FOR PRODUCTION USE


#IMPORTS
# logging.basicConfig(
#     encoding="utf-8",
#     level=logging.DEBUG,
#     format="%(asctime)s %(levelname)s: %(name)s: Line: %(lineno)s - %(funcName)s(): %(message)s",
#     filename='dev_log.log'
# )

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter("%(asctime)s %(levelname)s: %(name)s: Line: %(lineno)s - %(funcName)s(): %(message)s")
file_handler = logging.FileHandler('dev_log.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.WARNING)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)



def _main_validation(document_data, full_page_raw, doc_title_output):

    def log_info(text):
        logger.info(text)

    def log_warn(text):
        logger.warning(text)

    def log_debug(text):
        logger.debug(text)

    
    
    try:
        customer_data = document_data.get("customer")
        customer_data = customer_data[0]
        doc_titles = doc_title_output
    except:
        customer_data = doc_title_output['customer'][0]
        doc_titles = doc_title_output['titles']

    COMMENT_GENERATOR = False

    #MAINLINE

    #MAINBLOCK

    rejected_documents = [d for d in rejected_documents if d.get('page_type') not in ['blank_page', 'unknown_page']]
    return_data = {}
    # return_data = {"customer": mapped_customers, "documents": document_data, "mapped_data": mapped_data, "rejected_documents": rejected_documents, "non_downloaded": non_downloaded}
    # filename = run_reporting(application_data, validated_docs)

    return return_data, filename
