from uuid import UUID

from flows_sdk import utils
from flows_sdk.utils import workflow_input
from flows_sdk.types import HsBlockInstance
from flows_sdk.blocks import PythonBlock
from flows_sdk.flows import Flow, Manifest, Parameter
from flows_sdk.implementations.idp_v35 import idp_blocks, idp_values
from flows_sdk.implementations.idp_v35.idp_blocks import (
    IDPFullPageTranscriptionBlock, IDPImageCorrectionBlock, IDPOutputsBlock,
    SubmissionBootstrapBlock, SubmissionCompleteBlock)
from flows_sdk.implementations.idp_v35.idp_values import (IDPTriggers,
                                                          IdpWorkflowConfig,
                                                          get_idp_wf_config,
                                                          get_idp_wf_inputs)
from flows_sdk.package_utils import export_flow
from typing import Any

IDENTIFIER = "#IDENTIFIER"
FLOW_UUID = "#FLOWUUID"

class FlowInputs:
    URL = 'URL'
    API_KEY = 'API_KEY'


def idp_workflow(idp_wf_config: IdpWorkflowConfig) -> Flow:

    bootstrap_submission = idp_blocks.SubmissionBootstrapBlock(
        reference_name='submission_bootstrap',
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

    manual_identificaiton = idp_blocks.ManualIdentificationBlock(
        reference_name='manual_identification',
        submission=machine_identification.output('submission'),
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

    flexible_extraction = idp_blocks.FlexibleExtractionBlock(
        reference_name='flexible_extraction',
        submission=manual_transcription.output('submission'),
        api_params=bootstrap_submission.output('api_params'),
        task_restrictions=idp_wf_config.flexible_extraction_config.task_restrictions,
        supervision_transcription_masking=(
            idp_wf_config.flexible_extraction_config.supervision_transcription_masking
        ),
    )


    def _load_submission(submission: any) -> any:
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
            _hs_block_instance.log(f"DEBUG: {text}", HsBlockInstance.LogLevel.INFO)

        doc_titles = doc_title_output['titles']

        sub_id = document_data['submission']['id']

        #MAINLINE

        #MAINBLOCK



    function_validation = PythonBlock(
            reference_name="validation",
            code=_main_validation,
            code_input= {
                "document_data": machine_transcription.output(),
                "full_page_raw": full_page_transcription.output(),
                "doc_title_output": load_submission.output(),
                "domain": workflow_input(FlowInputs.URL),
                "api_key": workflow_input(FlowInputs.API_KEY),
                },
            title="Perform Validations",
            description="Perform Validations",
        )

    submission_complete = idp_blocks.SubmissionCompleteBlock(
        reference_name='complete_submission', submission=flexible_extraction.output('submission')
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
            bootstrap_submission,
            case_collation_task,
            machine_classification,
            manual_classification,
            machine_identification,
            manual_identificaiton,
            machine_transcription,
            manual_transcription,
            flexible_extraction,
            load_submission,
            image_correction,
            full_page_transcription,
            function_validation,
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