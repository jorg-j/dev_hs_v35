# Build Version: #VERSION
# HyperScience Build Version
from uuid import UUID

from flows_sdk import utils
from flows_sdk.utils import workflow_input
from flows_sdk.types import HsBlockInstance
from flows_sdk.blocks import PythonBlock, Block, CodeBlock
from flows_sdk.flows import Flow, Manifest, Parameter
from flows_sdk.implementations.idp_v35 import idp_blocks, idp_values
from flows_sdk.implementations.idp_v35.idp_blocks import (
    IDPFullPageTranscriptionBlock, IDPImageCorrectionBlock, IDPOutputsBlock,
    SubmissionBootstrapBlock, SubmissionCompleteBlock)
from flows_sdk.implementations.idp_v35.idp_values import (IDPTriggers,
                                                            IDPManifest,
                                                          IdpWorkflowConfig,
                                                          get_idp_wf_config,
                                                          get_idp_wf_inputs)
from flows_sdk.package_utils import export_flow
from typing import Any, Dict

IDENTIFIER = "#IDENTIFIER"
FLOW_UUID = "#FLOWUUID"

class FlowInputs:
    URL = 'URL'
    API_KEY = 'API_KEY'

class CustomParams:
    FileUpload: str = 'file'


def idp_workflow(idp_wf_config: IdpWorkflowConfig) -> Flow:

    # IDP manifest
    manifest: IDPManifest = IDPManifest(flow_identifier=IDENTIFIER)

    def _build_config_dict(file_uuid: str, _hs_block_instance: HsBlockInstance) -> Dict:

        config = {}

        config['fa5dc5eb-4296-430c-92a9-5a71617a24ab'] = {
            'name': 'LAYOUTNAMEHERE',
            'field': None,
            'pages': 1,
        }

        return config

    build_config_dict = CodeBlock(
        reference_name='build_config_dict',
        code=_build_config_dict,
        code_input={'file_uuid': workflow_input(CustomParams.FileUpload)},
        title='Build Config',
        description='Builds layout level configuration',
    )

    bootstrap_submission = idp_blocks.SubmissionBootstrapBlock(
        reference_name='submission_bootstrap'
    )


    image_correction = IDPImageCorrectionBlock(
        reference_name='image_correction', submission=bootstrap_submission.output('submission')
    )



    full_page_transcription = IDPFullPageTranscriptionBlock(
        reference_name='full_page_transcription', submission=image_correction.output('submission')
    )


    case_collation_task = idp_blocks.MachineCollationBlock(
        reference_name='machine_collation',
        submission=bootstrap_submission.output('submission'),
        cases=bootstrap_submission.output('api_params.cases'),
    )

    machine_classification = idp_blocks.MachineClassificationBlock(
        reference_name='machine_classification',
        submission=case_collation_task.output('submission'),
        api_params=bootstrap_submission.output('api_params'),
        rotation_correction_enabled=idp_wf_config.rotation_correction_enabled,
        mobile_processing_enabled=False,
    )

    manual_classification = idp_blocks.ManualClassificationBlock(
        reference_name='manual_classification',
        submission=machine_classification.output('submission'),
        api_params=bootstrap_submission.output('api_params'),
    )

    machine_identification = idp_blocks.MachineIdentificationBlock(
        reference_name='machine_identification',
        submission=manual_classification.output('submission'),
        api_params=bootstrap_submission.output('api_params'),
    )

    # Update fields to skip manual ID (except the one indicated)
    def _set_fields_to_skip(submission: Dict, config: str) -> Any:

        for document in submission.get('documents', []):
            field_name = config.get(document.get('layout_uuid'), {}).get('field', None)

            # Need to identify splitter fields so force ID on those and skip everything else
            if field_name:

                page_count = len(document.get('pages', []))
                identifier_count = 0

                # First Pass sets fields to skip and gets a count of the target field
                for field in document.get('document_fields', []):
                    if field.get('field_name') != field_name:
                        field.update(process_manual_identification_type='SKIP')
                        field.update(process_manual_transcription_type='SKIP')
                    else:
                        identifier_count += 1

                document['page_count'] = page_count
                document['identifier_count'] = identifier_count

                # Second pass forces field ID, or skips it because the machine has predicted
                # correctly (assumption being one identifier on each page)
                for field in document.get('document_fields', []):
                    if field.get('field_name') == field_name:
                        if page_count != identifier_count:
                            field.update(identification_confidence='not_sure')
                            field.update(process_manual_identification_type='FORCE')
                        else:
                            field.update(process_manual_identification_type='SKIP')
                            field.update(process_manual_transcription_type='SKIP')

            else:  # Skip ID and Transcription of all fields as we're using defined page counts
                for field in document.get('document_fields', []):
                    field.update(process_manual_identification_type='SKIP')
                    field.update(process_manual_transcription_type='SKIP')

            # Always skip tables in the first round
            for table in document.get('tables', []):
                table.update(process_manual_identification_type='SKIP')

                for column in table.get('columns', []):
                    for cell in column.get('cells', []):
                        cell.update(process_manual_transcription_type='SKIP')

        return {'submission': submission}

    set_fields_to_skip = CodeBlock(
        reference_name='set_fields_to_skip',
        code=_set_fields_to_skip,
        code_input={
            'submission': machine_identification.output('submission'),
            'config': build_config_dict.output(),
        },
        title='Manual ID Bypass',
        description='',
    )

    manual_identificaiton = idp_blocks.ManualIdentificationBlock(
        reference_name='manual_identification',
        submission=set_fields_to_skip.output('submission'),
        api_params=bootstrap_submission.output('api_params'),
    )

    machine_transcription = idp_blocks.MachineTranscriptionBlock(
        reference_name='machine_transcription',
        submission=manual_identificaiton.output('submission'),
        api_params=bootstrap_submission.output('api_params'),
    )

    manual_transcription = idp_blocks.ManualTranscriptionBlock(
        reference_name='manual_transcription',
        submission=machine_transcription.output('submission'),
        api_params=bootstrap_submission.output('api_params'),
        table_output_manual_review=(
            idp_wf_config.manual_transcription_config.table_output_manual_review
        ),
        supervision_transcription_masking=(
            idp_wf_config.manual_transcription_config.supervision_transcription_masking
        ),
        task_restrictions=idp_wf_config.manual_transcription_config.task_restrictions,
    )

    def _find_document_pages(submission: Dict, config: Dict) -> Any:

        submission_documents = {}
        submission_pages = None

        # Organize document splits based on either Field Name or known # of Pages
        # Field name takes priority
        for document in submission.get('documents', []):

            # We're assuming that documents will be derived from the same submission file
            file_uuid = document.get('pages', [])[0].get('file_uuid')
            key = document.get('layout_uuid') + ':' + file_uuid

            # Organizing by Layout UUID
            if key not in submission_documents:
                submission_documents.setdefault(key, [])

            field_name = config.get(document.get('layout_uuid'), {}).get('field', None)
            num_pages = config.get(document.get('layout_uuid'), {}).get('pages', 0)
            document_pages = len(document.get('pages', []))
            if not submission_pages:
                submission_pages = document_pages
            else:
                submission_pages += document_pages

            document_template = {
                'value': None,
                'pages': [],
                'first_page': None,
                'last_page': None,
                'combined_pages': document_pages,
                'submission_pages': submission_pages,
            }
            new_document = document_template.copy()

            if field_name:
                prev_field_value = None
                curr_field_value = None

                for field in document.get('document_fields', []):
                    if field.get('field_name') == field_name:

                        for page in document.get('pages', []):
                            if page.get('document_page_number') == field.get('page_number'):
                                submission_page_number = page.get('submission_page_number')

                        if not prev_field_value:
                            prev_field_value = (
                                field.get('transcription')
                                if not field.get('transcription_normalized')
                                else field.get('transcription_normalized')
                            )
                            curr_field_value = prev_field_value
                        else:
                            curr_field_value = (
                                field.get('transcription')
                                if not field.get('transcription_normalized')
                                else field.get('transcription_normalized')
                            )

                        if prev_field_value == curr_field_value:
                            new_document.get('pages', []).append(submission_page_number)
                            if not new_document.get('value'):
                                new_document.update(value=curr_field_value)
                                new_document.update(first_page=submission_page_number)
                        else:
                            # Append the Current Document
                            new_document.get('pages', []).sort()
                            new_document.update(last_page=new_document.get('pages', [])[-1])
                            submission_documents.get(key, []).append(new_document)

                            # Create a new instance
                            new_document = document_template.copy()
                            new_document.clear()
                            new_document.update(value=None)
                            new_document.update(pages=[])
                            new_document.update(first_page=None)
                            new_document.update(last_page=None)
                            new_document.update(combined_pages=document_pages)
                            new_document.update(submission_pages=submission_pages)

                            new_document.get('pages', []).append(submission_page_number)
                            new_document.update(value=curr_field_value)
                            new_document.update(first_page=submission_page_number)
                            prev_field_value = curr_field_value

                # Ensure the last created document gets stored in the submission documents
                new_document.update(last_page=new_document.get('pages', [])[-1])
                submission_documents.get(key, []).append(new_document)
            elif num_pages != 0:
                page_count = len(document.get('pages', []))

                for inx, page in enumerate(document.get('pages', [])):
                    if inx == 0:
                        new_document = document_template.copy()
                        new_document.get('pages', []).append(page.get('submission_page_number'))
                        if page_count == 1:
                            new_document.update(first_page=new_document.get('pages', [])[0])
                            new_document.update(last_page=new_document.get('pages', [])[0])
                            submission_documents.get(key, []).append(new_document)
                    elif inx + 1 == page_count:
                        if inx % num_pages > 0:
                            new_document.get('pages', []).append(page.get('submission_page_number'))
                            new_document.get('pages', []).sort()
                            new_document.update(first_page=new_document.get('pages', [])[0])
                            new_document.update(last_page=new_document.get('pages', [])[-1])
                            submission_documents.get(key, []).append(new_document)
                        else:
                            new_document.update(first_page=new_document.get('pages', [])[0])
                            new_document.update(last_page=new_document.get('pages', [])[-1])
                            submission_documents.get(key, []).append(new_document)

                            new_document = document_template.copy()
                            new_document.update(value=None)
                            new_document.update(pages=[])
                            new_document.update(first_page=None)
                            new_document.update(last_page=None)
                            new_document.update(combined_pages=document_pages)
                            new_document.update(submission_pages=submission_pages)
                            new_document.get('pages', []).append(page.get('submission_page_number'))
                            new_document.get('pages', []).sort()
                            submission_documents.get(key, []).append(new_document)
                    elif inx % num_pages == 0:
                        new_document.update(first_page=new_document.get('pages', [])[0])
                        new_document.update(last_page=new_document.get('pages', [])[-1])
                        submission_documents.get(key, []).append(new_document)

                        new_document = document_template.copy()
                        new_document.update(value=None)
                        new_document.update(pages=[])
                        new_document.update(first_page=None)
                        new_document.update(last_page=None)
                        new_document.update(combined_pages=document_pages)
                        new_document.update(submission_pages=submission_pages)
                        new_document.get('pages', []).append(page.get('submission_page_number'))
                        new_document.get('pages', []).sort()
                    else:
                        new_document.get('pages', []).append(page.get('submission_page_number'))
            else:
                # Document doesn't have config, add whole document
                new_document = document_template.copy()
                new_document.clear()
                new_document.update(value=None)
                new_document.update(pages=[page.get('submission_page_number') for page in document.get('pages', [])])
                new_document.get('pages', []).sort()
                new_document.update(first_page=new_document.get('pages',[])[0])
                new_document.update(last_page=new_document.get('pages',[])[-1])
                new_document.update(combined_pages=document_pages)
                new_document.update(submission_pages=submission_pages)
                submission_documents.get(key, []).append(new_document)

        document_keys = list(submission_documents.keys())
        for key in document_keys:
            layout_uuid = key.split(':')[0]
            field_name = config.get(layout_uuid, {}).get('field', None)

            if field_name:
                documents = submission_documents.get(key)

                for jndx, document in enumerate(documents):

                    pages = document.get('pages', []).copy()
                    page_count = len(pages)
                    for kndx, page in enumerate(pages):
                        if kndx != page_count - 1:
                            if pages[kndx + 1] - pages[kndx] > 1:
                                print(pages[kndx], pages[kndx + 1])
                                diff = pages[kndx + 1] - pages[kndx]
                                j = 1
                                while j < diff:
                                    document.get('pages', []).append(pages[kndx] + j)
                                    j += 1

                    document.get('pages', []).sort()

                    if jndx + 1 < len(documents):
                        end_page = document.get('pages', [])[-1]
                        start_page = documents[jndx + 1].get('pages', [])[0]

                        if start_page - end_page >= 1:
                            diff = start_page - end_page
                            i = 1
                            while i < diff:
                                document.get('pages', []).append(end_page + i)
                                i += 1
                    else:
                        end_page = document.get('pages', [])[-1]
                        document_end = (
                            document.get('combined_pages')
                            if document.get('combined_pages') == document.get('submission_pages')
                            else document.get('submission_pages')
                        )

                        if document_end - end_page >= 1:
                            diff = document_end - end_page
                            i = 1
                            while i <= diff:
                                document.get('pages', []).append(end_page + i)
                                i += 1

                    document['pages'] = sorted(document['pages'])

        return submission_documents

    find_document_pages = CodeBlock(
        reference_name='find_document_pages',
        code=_find_document_pages,
        code_input={
            'submission': manual_transcription.output('submission'),
            'config': build_config_dict.output(),
        },
        title='Find Document Pages',
        description='',
    )

    machine_classification_2 = idp_blocks.MachineClassificationBlock(
        reference_name='machine_classification_two',
        submission=case_collation_task.output('submission'),
        api_params=bootstrap_submission.output('api_params'),
        rotation_correction_enabled=idp_wf_config.rotation_correction_enabled,
    )

    manual_classification_2 = idp_blocks.ManualClassificationBlock(
        reference_name='manual_classification_two',
        submission=machine_classification_2.output('submission'),
        api_params=bootstrap_submission.output('api_params'),
    )

    def _split_documents(submission: Dict, document_pages: Dict) -> Any:
        import uuid

        def _create_doc(doc_uuid: str, layout_version_uuid: str, page_ids: Any) -> Dict[str, Any]:
            return {
                'uuid': doc_uuid,
                'layout_version_uuid': layout_version_uuid,
                'pages': [
                    {
                        'submission_page_id': page_id,
                        'page_number': ix,
                        'classification_type': 'machine',
                    }
                    for ix, page_id in enumerate(page_ids, start=1)
                ],
                'metadata': {},
            }

        documents_out = []

        for document in submission.get('documents', []):
            layout_version_uuid = document.get('layout_version_uuid')
            key = document.get('layout_uuid') + ':' + document.get('pages', [])[0].get('file_uuid')

            subdivisions = document_pages.get(key, [])
            #if subdivisions:
            for sub in subdivisions:
                page_ids = []
                for page in document.get('pages', []):
                    if page.get('submission_page_number') in sub.get('pages', []):
                        page_ids.append(page.get('id'))
                        
                if len(page_ids) > 0:
                    documents_out.append(_create_doc(str(uuid.uuid4()), layout_version_uuid, page_ids))
            # else:
            #     documents_out.append(_create_doc(str(uuid.uuid4()), document.get('layout_version_uuid'), [page.get('id') for page in document.get('pages',[])]))

        return documents_out

    split_documents = CodeBlock(
        reference_name='split_documents',
        code=_split_documents,
        code_input={
            'submission': manual_classification_2.output('submission'),
            'document_pages': find_document_pages.output(),
        },
        title='Split Documents',
        description='',
    )

    sync_new_docs = Block(
        identifier='IDP_SYNC',
        reference_name='sync_new_docs',
        title='Sync New Documents',
        input={
            'api_domain': 'document',
            'api_method': 'sync',
            'api_payload': {
                'submission_id': manual_classification_2.output('submission.id'),
                'documents': split_documents.output(),
                'layout_release_uuid': workflow_input('layout_release_uuid'),
            },
        },
    )

    merge_new_documents = CodeBlock(
        reference_name='new_code_block',
        code=lambda submission, documents: {**submission, 'documents': documents},
        code_input={
            'submission': manual_classification_2.output('submission'),
            'documents': sync_new_docs.output('documents'),
        },
        title='Merge Submission Documents',
        description='',
    )

    machine_identification_2 = idp_blocks.MachineIdentificationBlock(
        reference_name='machine_identification_2',
        # submission=merge_submission_data_3.output('submission'),
        submission=merge_new_documents.output(),
        api_params=bootstrap_submission.output('api_params'),
    )

    # Update fields to skip manual ID (except the one indicated)
    def _set_fields_to_skip_2(submission: Dict, config: Dict) -> Any:

        for document in submission.get('documents', []):
            field_name = config.get(document.get('layout_uuid'), {}).get('field', None)
            if field_name:
                page_count = len(document.get('pages', []))
                identifier_count = 0

                # First Pass sets fields to skip and gets a count of the target field
                for field in document.get('document_fields', []):
                    if field.get('field_name') == field_name:
                        identifier_count += 1

                # Second pass forces field ID, or skips it because the machine has predicted
                # correctly (assumption being one identifier on each page)
                for field in document.get('document_fields', []):
                    if field.get('field_name') == field_name:
                        if page_count != identifier_count:
                            field.update(identification_confidence='not_sure')
                            field.update(process_manual_identification_type='FORCE')
                        else:
                            field.update(process_manual_identification_type='SKIP')
                            field.update(process_manual_transcription_type='SKIP')

                document['page_count'] = page_count
                document['identifier_count'] = identifier_count

        return {'submission': submission}

    set_fields_to_skip_2 = CodeBlock(
        reference_name='set_fields_to_skip_2',
        code=_set_fields_to_skip_2,
        code_input={
            'submission': machine_identification_2.output('submission'),
            'config': build_config_dict.output(),
        },
        title='Manual ID Bypass',
        description='',
    )

    manual_identification_2 = idp_blocks.ManualIdentificationBlock(
        reference_name='manual_identification_2',
        # submission=machine_identification.output('submission'),
        submission=set_fields_to_skip_2.output('submission'),
        api_params=bootstrap_submission.output('api_params'),
        task_restrictions=idp_wf_config.manual_identification_config.task_restrictions,
    )

    machine_transcription_2 = idp_blocks.MachineTranscriptionBlock(
        reference_name='machine_transcription_2',
        submission=manual_identification_2.output('submission'),
        api_params=bootstrap_submission.output('api_params'),
    )

    manual_transcription_2 = idp_blocks.ManualTranscriptionBlock(
        reference_name='manual_transcription_2',
        submission=machine_transcription_2.output('submission'),
        api_params=bootstrap_submission.output('api_params'),
        supervision_transcription_masking=(
            idp_wf_config.manual_transcription_config.supervision_transcription_masking
        ),
        table_output_manual_review=(
            idp_wf_config.manual_transcription_config.table_output_manual_review
        ),
        task_restrictions=idp_wf_config.manual_transcription_config.task_restrictions,
    )


    flexible_extraction = idp_blocks.FlexibleExtractionBlock(
        reference_name='flexible_extraction',
        submission=manual_transcription_2.output('submission'),
        api_params=bootstrap_submission.output('api_params'),
        task_restrictions=idp_wf_config.flexible_extraction_config.task_restrictions,
        supervision_transcription_masking=(
            idp_wf_config.flexible_extraction_config.supervision_transcription_masking
        ),
    )


    def _load_submission(submission):
        import inspect
        import json
        import io

        response = {}

        submission_id_ref = submission['id']
        proxy = inspect.stack()[1].frame.f_locals['proxy']

        r = proxy.sdm_get(f'api/v5/submissions/{submission_id_ref}?flat=False', timeout=10)
        response['titles'] = r.json()


        return response

    load_submission = PythonBlock(
        reference_name='load_submission',
        code=_load_submission,
        code_input={'submission': flexible_extraction.output('submission')},
        title='Load Submission',
        description='Returns Submission in API v5 Format',
    )

    URL = Parameter(
        name=FlowInputs.URL,
        title='API URL',
        type='string',
        optional=False)

    API_KEY = Parameter(
        name=FlowInputs.API_KEY,
        title='API KEY',
        type='string',
        secret=True,
        optional=False)


    def log_runner(text: str, _hs_block_instance: HsBlockInstance):
        _hs_block_instance.log(f'{text}', HsBlockInstance.LogLevel.INFO)

    def _main_validation(document_data, full_page_raw, doc_title_output, domain, api_key, _hs_block_instance: HsBlockInstance):
        #IMPORTS
        
        def log_info(text):
            _hs_block_instance.log(f"INFO: {text}", HsBlockInstance.LogLevel.INFO)

        def log_warn(text):
            _hs_block_instance.log(f"WARNING: {text}", HsBlockInstance.LogLevel.WARN)

        def log_debug(text):
            pass

        doc_titles = doc_title_output['titles']

        sub_id = document_data['submission']['id']

        COMMENT_GENERATOR = False

        #MAINLINE

        #MAINBLOCK

        rejected_documents = [d for d in rejected_documents if d.get('page_type') not in ['blank_page', 'unknown_page']]


    function_validation = PythonBlock(
            reference_name="validation",
            code=_main_validation,
            code_input= {
                "document_data": machine_transcription_2.output(),
                "full_page_raw": full_page_transcription.output(),
                "doc_title_output": load_submission.output(),
                "domain": workflow_input(FlowInputs.URL),
                "api_key": workflow_input(FlowInputs.API_KEY),
                },
            title="Perform Validations",
            description="Perform Validations",
        )


    def _mark_as_complete(submission: Dict, key_fields_sub: Dict) -> Dict:
        from datetime import datetime

        def _convert_field(field: Dict, page_id: int, page_url: str) -> Dict:
            for location in field.get('locations', []):
                position = location.get('position')

            # pylint: disable=line-too-long
            template = {
                'id': field.get('id'),
                'state': 'complete',
                'substate': None,
                'exceptions': [],
                'name': field.get('field_name'),
                'output_name': field.get('output_name'),
                'field_definition_attributes': {
                    'required': False,
                    'data_type': None,
                    'multiline': False,
                    'routing': False,
                    'duplicate': False,
                    'supervision_override': False,
                },
                'transcription': {
                    'raw': field.get('transcription'),
                    'normalized': field.get('transcription_normalized'),
                    'source': field.get('transcription_source'),
                    'data_deleted': False,
                    'user_transcribed': None,
                },
                'field_image_url': f"{page_url}?start_x={field.get('bounding_box')[0]}&start_y={field.get('bounding_box')[1]}5&end_x={field.get('bounding_box')[2]}&end_y={field.get('bounding_box')[3]}",
                'page_id': page_id,
                'occurrence_index': field.get('occurance_index'),
                'locations': [
                    {
                        'position': position,
                        'page_id': page_id,
                        'location_image_url': f"{page_url}?start_x={field.get('bounding_box')[0]}&start_y{field.get('bounding_box')[1]}&end_x={field.get('bounding_box')[2]}&end_y={field.get('bounding_box')[3]}",
                    }
                ],
                'decisions': [],
            }
            # pylint: enable=line-too-long

            return template

        dt_completed = datetime.isoformat(datetime.utcnow())
        dt_completed_fmt = dt_completed + 'Z'

        for document in submission.get('documents', []):
            document['state'] = 'complete'
            document['complete_time'] = dt_completed_fmt

            for page in document.get('pages', []):
                page['state'] = 'complete'

                for k_doc in key_fields_sub.get('documents', []):
                    for k_field in k_doc.get('document_fields', []):
                        if (
                            k_field.get('page_number') == page.get('submission_page_number')
                            and k_field.get('bounding_box') is not None
                        ):
                            cvt_field = _convert_field(
                                k_field, page.get('id'), page.get('corrected_image_url')
                            )
                            document.get('document_fields', []).append(cvt_field)

            for field in document.get('document_fields', []):
                field['state'] = 'complete'

            for cell in [
                cell
                for document_table in document.get('document_tables', [])
                for row in document_table.get('rows', [])
                for cell in row.get('cells', [])
            ]:
                cell['state'] = 'complete'

        for page in submission.get('unassigned_pages', []):
            page['state'] = 'complete'

        if 'state' in submission:
            submission['state'] = 'complete'
        if 'complete_time' in submission:
            submission['complete_time'] = dt_completed_fmt

        return submission

    mark_as_complete = CodeBlock(
        reference_name='mark_as_complete',
        title='Mark As Complete',
        description='Mark submission as complete',
        code=_mark_as_complete,
        code_input={
            'submission': load_submission.output(),
            'key_fields_sub': manual_transcription.output('submission'),
        },
    )

    submission_complete = idp_blocks.SubmissionCompleteBlock(
        reference_name='complete_submission',
        submission=flexible_extraction.output('submission')
    )

    outputs = idp_blocks.IDPOutputsBlock(
        inputs={'submission': bootstrap_submission.output('submission')}
    )


    inputs = get_idp_wf_inputs(idp_wf_config)

    inputs[FlowInputs.URL] = 'DOMAIN HERE'
    inputs[FlowInputs.API_KEY] = 'API KEY HERE'

    custom_manifest = idp_values.IDPManifest(flow_identifier=IDENTIFIER)
    custom_manifest.input.append(URL)
    custom_manifest.input.append(API_KEY)


    return Flow(
        uuid=UUID(FLOW_UUID),
        owner_email='foo@baa.com',
        title="#FLOWTITLE",
        description="#FLOWTITLE",
        manifest=custom_manifest,
        triggers=idp_values.IDPTriggers(),
        input=inputs,
        blocks=[
            build_config_dict,
            bootstrap_submission,
            case_collation_task,
            machine_classification,
            manual_classification,
            machine_identification,
            set_fields_to_skip,
            manual_identificaiton,
            machine_transcription,
            manual_transcription,
            find_document_pages,
            machine_classification_2,
            manual_classification_2,
            split_documents,
            sync_new_docs,
            merge_new_documents,
            machine_identification_2,
            set_fields_to_skip_2,
            manual_identification_2,
            machine_transcription_2,
            manual_transcription_2,
            image_correction,
            full_page_transcription,
            flexible_extraction,
            load_submission,
            function_validation,
            mark_as_complete,
            submission_complete,
            outputs,
        ],
        output={"submission": submission_complete.output()},
    )


def entry_point_idp_flow() -> Flow:
    idp_wf_conig = get_idp_wf_config()
    return idp_workflow(idp_wf_conig)

if __name__ == "__main__":
    export_flow(flow=entry_point_idp_flow())