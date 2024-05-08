# implement a cache
cache = {}


def cache_read(key):
    """
    Reads from the cache - shockingly
    """
    return cache.get(key, None)


def cache_write(key, value):
    """
    Writes to the cache
    """
    cache[key] = value


def cache_clear():
    """
    Clear the cache
    """
    cache = {}


def get_validation(layout_name):
    """
    Get the specific function to process the validation
    """
    function_map = {
        Layouts.doc017: perform_doc17,
        Layouts.doc018a: perform_doc18,
        Layouts.doc020: perform_doc20,
        Layouts.doc021: perform_doc21,
        Layouts.doc022: perform_doc22,
        Layouts.doc029: perform_doc29,
        Layouts.doc030: perform_doc30,
    }

    return function_map.get(layout_name)


# Setup the original rejected documents array
try:
    rejected_documents = document_data["submission"]["unassigned_pages"]
except KeyError:
    rejected_documents = []

hs_submission_id = document_data.get("submission", {}).get("id", 0)

# Document to Full page link
document_data = document_to_full_page(document_data, full_page_raw)

# Map filenames to documents
document_data = map_filename(
    document_data, doc_titles, customer_data
)  # Map the filenames

# determine documents which were not throughput

# accuracy reader


# Map filenames to rejected documents
rejected_documents_named = map_filename(rejected_documents, doc_titles, customer_data)

# Reject documents when they do not meet quality standards
document_data_quality_met, rejected_quality = perform_document_quality_checks(
    document_data
)

# Remove DVAData from the rejected documents listing as it is not a document
rejected_documents_src = [
    document
    for document in rejected_documents_named
    if not document["filename"].endswith("DVAData.pdf")
]

# Prepare document connections
application_data = document_connections(customer_data, document_data_quality_met)

# process validations
process_docids = application_data.get("doc_ids", {}).keys()

validated_docs = []
all_processed_docs = []

document_data = perform_transformations(document_data)

accuracy_reader(document_data)

# Enables metadata storage in application_data
application_data['metadata'] = {}

guarded_docs = []
all_guarded_docs = []
guard = None
for doc_id in process_docids:
    for document in document_data:
        if doc_id == document.get("id", 0):
            layout_name = document.get("layout_name", "")
            active_document = document
            break
    validation = get_validation(layout_name)
    if validation is not None:
        try:
            results, guard = validation(application_data, active_document)
        except Exception as e:
            guard = True
            log_warn(f"VALERR {e}")
        if not guard:
            all_processed_docs.append(active_document)
            validated_docs.append(results)
            
            # if doc19 then add to application data, used in doc32 val 0
            if layout_name in Layouts.doc019_d32v0 and results.doc_pass:
                application_data['metadata']['doc019_success_flag'] = True

    if guard or validation is None:
        guarded_docs.append(doc_id)
        all_guarded_docs.append(active_document)
        rejected_documents.append(active_document)

# process reporting
application_data["hs_submission_id"] = hs_submission_id
filename = run_reporting(
    application_data, document_data, document_validations=validated_docs
)
