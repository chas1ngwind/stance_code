#!/usr/bin/env python
# coding: utf-8

# In[9]:


import torch
import random
import numpy as np
import os

from tqdm import tqdm, trange
# torch.cuda.empty_cache()
from torch.utils.data import TensorDataset, DataLoader, RandomSampler, SequentialSampler
from pytorch_pretrained_bert.optimization import BertAdam


# In[10]:


from run_classifier import NegProcessor, generate_opp_dataset, convert_opp_pers_to_features, convert_opp_claims_to_features, StanceProcessor, MrpcProcessor, logger, convert_examples_to_features,   set_optimizer_params_grad, copy_optimizer_params_to_model, accuracy, p_r_f1, tp_pcount_gcount, convert_claims_to_features, convert_pers_to_features


# In[11]:


if torch.cuda.is_available():    

    # Tell PyTorch to use the GPU.    
    device = torch.device("cuda")
    n_gpu = torch.cuda.device_count()
    logger.info('There are %d GPU(s) available.' % (n_gpu))
    logger.info('We will use the GPU: ')
    logger.info(torch.cuda.get_device_name(0))

# If not...
else:
    logger.info('No GPU available, using the CPU instead.')
    device = torch.device("cpu")


# In[12]:


from transformers import BertTokenizer, AdamW, get_linear_schedule_with_warmup
from pytorch_pretrained_bert.modeling import BertForSequenceClassification, BertPreTrainedModel, BertModel, BertConfig
from torch.nn import BCEWithLogitsLoss, CosineEmbeddingLoss,CrossEntropyLoss, MSELoss


# In[13]:


class BertForConsistencyCueClassification(BertPreTrainedModel):
    def __init__(self, config, num_labels=2):
        super(BertForConsistencyCueClassification, self).__init__(config)
        self.num_labels = num_labels

        self.bert = BertModel(config)
        self.dropout = torch.nn.Dropout(config.hidden_dropout_prob)
        self.classifier = torch.nn.Linear(config.hidden_size*4+1, num_labels)
        self.classifier2 = torch.nn.Linear(config.hidden_size*4, num_labels)
        self.apply(self.init_bert_weights)
#         self.init_weights()

#     @add_start_docstrings_to_callable(BERT_INPUTS_DOCSTRING)
    def forward(
        self,
        input_ids=None,
        attention_mask=None,
        token_type_ids=None,
        position_ids=None,
        head_mask=None,
        inputs_embeds=None,
        labels=None,
        
        input_ids2=None,
        attention_mask2=None,
        token_type_ids2=None,
        position_ids2=None,
        head_mask2=None,
        inputs_embeds2=None,
        labels2=None,
        
        input_ids3=None,
        attention_mask3=None,
        token_type_ids3=None,
        position_ids3=None,
        head_mask3=None,
        inputs_embeds3=None,
        labels3=None,
        
        input_ids4=None,
        attention_mask4=None,
        token_type_ids4=None,
        position_ids4=None,
        head_mask4=None,
        inputs_embeds4=None,
        labels4=None
    ):
        r"""
        labels (:obj:`torch.LongTensor` of shape :obj:`(batch_size,)`, `optional`, defaults to :obj:`None`):
            Labels for computing the sequence classification/regression loss.
            Indices should be in :obj:`[0, ..., config.num_labels - 1]`.
            If :obj:`config.num_labels == 1` a regression loss is computed (Mean-Square loss),
            If :obj:`config.num_labels > 1` a classification loss is computed (Cross-Entropy).

    Returns:
        :obj:`tuple(torch.FloatTensor)` comprising various elements depending on the configuration (:class:`~transformers.BertConfig`) and inputs:
        loss (:obj:`torch.FloatTensor` of shape :obj:`(1,)`, `optional`, returned when :obj:`label` is provided):
            Classification (or regression if config.num_labels==1) loss.
        logits (:obj:`torch.FloatTensor` of shape :obj:`(batch_size, config.num_labels)`):
            Classification (or regression if config.num_labels==1) scores (before SoftMax).
        hidden_states (:obj:`tuple(torch.FloatTensor)`, `optional`, returned when ``config.output_hidden_states=True``):
            Tuple of :obj:`torch.FloatTensor` (one for the output of the embeddings + one for the output of each layer)
            of shape :obj:`(batch_size, sequence_length, hidden_size)`.

            Hidden-states of the model at the output of each layer plus the initial embedding outputs.
        attentions (:obj:`tuple(torch.FloatTensor)`, `optional`, returned when ``config.output_attentions=True``):
            Tuple of :obj:`torch.FloatTensor` (one for each layer) of shape
            :obj:`(batch_size, num_heads, sequence_length, sequence_length)`.

            Attentions weights after the attention softmax, used to compute the weighted average in the self-attention
            heads.

    Examples::

        from transformers import BertTokenizer, BertForSequenceClassification
        import torch

        tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
        model = BertForSequenceClassification.from_pretrained('bert-base-uncased')

        input_ids = torch.tensor(tokenizer.encode("Hello, my dog is cute", add_special_tokens=True)).unsqueeze(0)  # Batch size 1
        labels = torch.tensor([1]).unsqueeze(0)  # Batch size 1
        outputs = model(input_ids, labels=labels)

        loss, logits = outputs[:2]

        """
# Pers rep
        _, outputs = self.bert(
            input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
#             position_ids=position_ids,
#             head_mask=head_mask,
#             inputs_embeds=inputs_embeds,
        )
# Claim rep
        _, outputs2 = self.bert(
            input_ids2,
            attention_mask=attention_mask2,
            token_type_ids=token_type_ids2,
#             position_ids=position_ids2,
#             head_mask=head_mask2,
#             inputs_embeds=inputs_embeds2,
        )
# Opp Pers rep        
        _, outputs3 = self.bert(
            input_ids3,
            attention_mask=attention_mask3,
            token_type_ids=token_type_ids3,
#             position_ids=position_ids2,
#             head_mask=head_mask2,
#             inputs_embeds=inputs_embeds2,
        )
# Opp Claim rep 
        _, outputs4 = self.bert(
            input_ids4,
            attention_mask=attention_mask4,
            token_type_ids=token_type_ids4,
#             position_ids=position_ids2,
#             head_mask=head_mask2,
#             inputs_embeds=inputs_embeds2,
        )
    
        pooled_output = outputs
        pooled_output2 = outputs2
        pooled_output3 = outputs3
        pooled_output4 = outputs4

        pooled_output = self.dropout(pooled_output)
        pooled_output2 = self.dropout(pooled_output2)
        pooled_output3 = self.dropout(pooled_output3)
        pooled_output4 = self.dropout(pooled_output4)
        
#         A series of different concatenations(concat(),|minus|,multiply, ...)
        final_output_cat = torch.cat((pooled_output2, pooled_output),1)
        final_output_minus = torch.abs(pooled_output2-pooled_output)
        final_output_mult = torch.mul(pooled_output2, pooled_output)
#         final_output_mimu = torch.cat((final_output_minus, final_output_mult),1)
#         final_output_camu = torch.cat((final_output_cat, final_output_mult),1)
#         final_output_cami = torch.cat((final_output_cat, final_output_minus),1)
        final_output_camimu = torch.cat((final_output_cat, final_output_minus, final_output_mult),1)
        cos_pooled_outputs = torch.cosine_similarity(pooled_output2, pooled_output, dim=1)
        
        
        
        ocop_final_output_cat = torch.cat((pooled_output4, pooled_output3),1)
        ocop_final_output_minus = torch.abs(pooled_output4-pooled_output3)
        ocop_final_output_mult = torch.mul(pooled_output4, pooled_output3)
#         final_output_mimu = torch.cat((final_output_minus, final_output_mult),1)
#         final_output_camu = torch.cat((final_output_cat, final_output_mult),1)
#         final_output_cami = torch.cat((final_output_cat, final_output_minus),1)
        ocop_final_output_camimu = torch.cat((ocop_final_output_cat, ocop_final_output_minus, ocop_final_output_mult),1)
        ocop_cos_pooled_outputs = torch.cosine_similarity(pooled_output4, pooled_output3, dim=1)
        

        cop_final_output_cat = torch.cat((pooled_output2, pooled_output3),1)
        cop_final_output_minus = torch.abs(pooled_output2-pooled_output3)
        cop_final_output_mult = torch.mul(pooled_output2, pooled_output3)
#         final_output_mimu = torch.cat((final_output_minus, final_output_mult),1)
#         final_output_camu = torch.cat((final_output_cat, final_output_mult),1)
#         final_output_cami = torch.cat((final_output_cat, final_output_minus),1)
        cop_final_output_camimu = torch.cat((cop_final_output_cat, cop_final_output_minus, cop_final_output_mult),1)
        cop_cos_pooled_outputs = torch.cosine_similarity(pooled_output2, pooled_output3, dim=1)
        

        ocp_final_output_cat = torch.cat((pooled_output4, pooled_output),1)
        ocp_final_output_minus = torch.abs(pooled_output4-pooled_output)
        ocp_final_output_mult = torch.mul(pooled_output4, pooled_output)
#         final_output_mimu = torch.cat((final_output_minus, final_output_mult),1)
#         final_output_camu = torch.cat((final_output_cat, final_output_mult),1)
#         final_output_cami = torch.cat((final_output_cat, final_output_minus),1)
        ocp_final_output_camimu = torch.cat((ocp_final_output_cat, ocp_final_output_minus, ocp_final_output_mult),1)
        ocp_cos_pooled_outputs = torch.cosine_similarity(pooled_output4, pooled_output, dim=1)
        
        
        
        
#         1
#         torch.Size([hidden_size*2, 768])
#         2
#         torch.Size([hidden_size, 768])
#         3
#         torch.Size([hidden_size, 768])
#         4
#         torch.Size([hidden_size*2, 768])
#         5
#         torch.Size([hidden_size*3, 768])
#         6
#         torch.Size([hidden_size*3, 768])
#         7
#         torch.Size([hidden_size*4, 768])
        
        batch_size = list(pooled_output.size())[0]
        hidden_size = list(pooled_output.size())[1]
        
        final_output_all = torch.cat((final_output_camimu, cos_pooled_outputs.unsqueeze(1)),1)
        cop_final_output_all = torch.cat((cop_final_output_camimu, cop_cos_pooled_outputs.unsqueeze(1)),1)
        ocp_final_output_all = torch.cat((ocp_final_output_camimu, ocp_cos_pooled_outputs.unsqueeze(1)),1)
        ocop_final_output_all = torch.cat((ocop_final_output_camimu, ocop_cos_pooled_outputs.unsqueeze(1)),1)
        
        logits_ce = self.classifier(final_output_all)
        
        ocop_logits_ce = self.classifier(ocop_final_output_all)
        cop_logits_ce = self.classifier(cop_final_output_all)
        ocp_logits_ce = self.classifier(ocp_final_output_all)
        
        
#         if input_ids4 and input_ids3:
        final_logits = logits_ce-(0.33*cop_logits_ce)-(0.33*ocp_logits_ce)+(0.33*ocop_logits_ce)
#         elif input_ids3:
#             final_logits = logits_ce-(0.33*cop_logits_ce)
#         elif input_ids4:
#             final_logits = logits_ce-(0.33*ocp_logits_ce)
#         else:
#             final_logits = logits_ce
#         print('logits_ce:')
#         print(logits_ce)
        
#         logits_ori = self.classifier2(final_output_camimu)
#         print('logits_ori:')
#         print(logits_ori)

        #Calculate loss during training process
        if labels is not None:
            if self.num_labels == 1:
                #  We are doing regression
                loss_fct = MSELoss()
                loss = loss_fct(final_logits.view(-1), labels.view(-1))
            else:
                loss_fct_ce = CrossEntropyLoss()
                loss_ce = loss_fct_ce(final_logits.view(-1, self.num_labels), labels.view(-1))
#                 logger.info('loss_ce:')
#                 logger.info(loss_ce)

#                 loss_ori = loss_fct_ce(logits_ori.view(-1, self.num_labels), labels.view(-1))
#                 print('loss_ori:')
#                 print(loss_ori)
                loss_fct_cos = CosineEmbeddingLoss()

                labels2[labels2==0] = -1
                loss_cos = loss_fct_cos(pooled_output, pooled_output2, labels2)
                labels2[labels2==-1] = 0
#                 logger.info('loss_cos:')
#                 logger.info(loss_cos)
            
                loss = loss_ce
#                 logger.info('final loss:')
#                 logger.info(loss)
                
#             outputs = (loss,) + outputs
#             outputs = (loss,) + logits_cos 
                outputs = loss
                return outputs
        else:
            #Get predictions when doing evaluation
            return final_logits
        
          # (loss), logits, (hidden_states), (attentions)

import csv
from pytorch_pretrained_bert.file_utils import PYTORCH_PRETRAINED_BERT_CACHE
def train_and_test(data_dir, bert_model="bert-base-uncased", task_name=None,
                   output_dir=None, max_seq_length=80, do_train=False, do_eval=False, do_lower_case=False,
                   train_batch_size=24, eval_batch_size=8, learning_rate=5e-5, num_train_epochs=5,
                   warmup_proportion=0.1,no_cuda=False, local_rank=-1, seed=42, gradient_accumulation_steps=1,
                   optimize_on_cpu=False, fp16=False, loss_scale=128, saved_model=""):
    


    # ## Required parameters
    # parser.add_argument("--data_dir",
    #                     default=None,
    #                     type=str,
    #                     required=True,
    #                     help="The input data dir. Should contain the .tsv files (or other data files) for the task.")
    # parser.add_argument("--bert_model", default=None, type=str, required=True,
    #                     help="Bert pre-trained model selected in the list: bert-base-uncased, "
    #                          "bert-large-uncased, bert-base-cased, bert-base-multilingual, bert-base-chinese.")
    # parser.add_argument("--task_name",
    #                     default=None,
    #                     type=str,
    #                     required=True,
    #                     help="The name of the task to train.")
    # parser.add_argument("--output_dir",
    #                     default=None,
    #                     type=str,
    #                     required=True,
    #                     help="The output directory where the model checkpoints will be written.")

    ## Other parameters
    # parser.add_argument("--max_seq_length",
    #                     default=128,
    #                     type=int,
    #                     help="The maximum total input sequence length after WordPiece tokenization. \n"
    #                          "Sequences longer than this will be truncated, and sequences shorter \n"
    #                          "than this will be padded.")
    # parser.add_argument("--do_train",
    #                     default=False,
    #                     action='store_true',
    #                     help="Whether to run training.")
    # parser.add_argument("--do_eval",
    #                     default=False,
    #                     action='store_true',
    #                     help="Whether to run eval on the dev set.")
    # parser.add_argument("--do_lower_case",
    #                     default=False,
    #                     action='store_true',
    #                     help="Set this flag if you are using an uncased model.")
    # parser.add_argument("--train_batch_size",
    #                     default=32,
    #                     type=int,
    #                     help="Total batch size for training.")
    # parser.add_argument("--eval_batch_size",
    #                     default=8,
    #                     type=int,
    #                     help="Total batch size for eval.")
    # parser.add_argument("--learning_rate",
    #                     default=5e-5,
    #                     type=float,
    #                     help="The initial learning rate for Adam.")
    # parser.add_argument("--num_train_epochs",
    #                     default=3.0,
    #                     type=float,
    #                     help="Total number of training epochs to perform.")
    # parser.add_argument("--warmup_proportion",
    #                     default=0.1,
    #                     type=float,
    #                     help="Proportion of training to perform linear learning rate warmup for. "
    #                          "E.g., 0.1 = 10%% of training.")
    # parser.add_argument("--no_cuda",
    #                     default=False,
    #                     action='store_true',
    #                     help="Whether not to use CUDA when available")
    # parser.add_argument("--local_rank",
    #                     type=int,
    #                     default=-1,
    #                     help="local_rank for distributed training on gpus")
    # parser.add_argument('--seed',
    #                     type=int,
    #                     default=42,
    #                     help="random seed for initialization")
    # parser.add_argument('--gradient_accumulation_steps',
    #                     type=int,
    #                     default=1,
    #                     help="Number of updates steps to accumulate before performing a backward/update pass.")
    # parser.add_argument('--optimize_on_cpu',
    #                     default=False,
    #                     action='store_true',
    #                     help="Whether to perform optimization and keep the optimizer averages on CPU")
    # parser.add_argument('--fp16',
    #                     default=False,
    #                     action='store_true',
    #                     help="Whether to use 16-bit float precision instead of 32-bit")
    # parser.add_argument('--loss_scale',
    #                     type=float, default=128,
    #                     help='Loss scaling, positive power of 2 values can improve fp16 convergence.')

    # args = parser.parse_args()

    
    processors = {
#         "cola": ColaProcessor,
#         "mnli": MnliProcessor,
        "mrpc": MrpcProcessor,
        "stance":StanceProcessor,
        "neg":NegProcessor
    }

    if local_rank == -1 or no_cuda:
        device = torch.device("cuda" if torch.cuda.is_available() and not no_cuda else "cpu")
        n_gpu = torch.cuda.device_count()
    else:
        device = torch.device("cuda", local_rank)
        n_gpu = 1
        # Initializes the distributed backend which will take care of sychronizing nodes/GPUs
        torch.distributed.init_process_group(backend='nccl')
        if fp16:
            logger.info("16-bits training currently not supported in distributed training")
            fp16 = False # (see https://github.com/pytorch/pytorch/pull/13496)
    logger.info("device %s n_gpu %d distributed training %r", device, n_gpu, bool(local_rank != -1))

    if gradient_accumulation_steps < 1:
        raise ValueError("Invalid gradient_accumulation_steps parameter: {}, should be >= 1".format(
                            gradient_accumulation_steps))

    train_batch_size = int(train_batch_size / gradient_accumulation_steps)

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if n_gpu > 0:
        torch.cuda.manual_seed_all(seed)

    if not do_train and not do_eval:
        raise ValueError("At least one of `do_train` or `do_eval` must be True.")

    if do_train:
#         if os.path.exists(output_dir) and os.listdir(output_dir):
        if os.path.exists(output_dir):
            pass
#             raise ValueError("Output directory ({}) already exists and is not empty.".format(output_dir))
        else:
            os.makedirs(output_dir, exist_ok=True)

    task_name = task_name.lower()

    if task_name not in processors:
        raise ValueError("Task not found: %s" % (task_name))

    processor = processors[task_name]()
    label_list = processor.get_labels()

#     tokenizer = BertTokenizer.from_pretrained(bert_model, do_lower_case=do_lower_case)
    tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
    

    train_examples = None
    num_train_steps = None
    if do_train:
        
        train_df = processor.get_train_df(data_dir)
        
        new_train_df = generate_opp_dataset(train_df)
        
        new_train_df.to_csv(os.path.join(data_dir, "new_train.tsv"),sep='\t',index=False)
        
        train_examples = processor.get_train_examples(data_dir)
        
        num_train_steps = int(
            len(train_examples) / train_batch_size / gradient_accumulation_steps * num_train_epochs)

    # Prepare model
#     model = BertForSequenceClassification.from_pretrained(bert_model,
#                 cache_dir=PYTORCH_PRETRAINED_BERT_CACHE / 'distributed_{}'.format(local_rank), num_labels = 2)

        model = BertForConsistencyCueClassification.from_pretrained('bert-base-uncased', num_labels=2)
        model.to(device)
        
        if fp16:
            model.half()

        if local_rank != -1:
            model = torch.nn.parallel.DistributedDataParallel(model, device_ids=[local_rank],
                                                              output_device=local_rank)
        elif n_gpu > 1:
            model = torch.nn.DataParallel(model)

        # Prepare optimizer
        if fp16:
            param_optimizer = [(n, param.clone().detach().to('cpu').float().requires_grad_())                                 for n, param in model.named_parameters()]
        elif optimize_on_cpu:
            param_optimizer = [(n, param.clone().detach().to('cpu').requires_grad_())                                 for n, param in model.named_parameters()]
        else:
            param_optimizer = list(model.named_parameters())
        no_decay = ['bias', 'gamma', 'beta']
        optimizer_grouped_parameters = [
            {'params': [p for n, p in param_optimizer if not any(nd in n for nd in no_decay)], 'weight_decay_rate': 0.01},
            {'params': [p for n, p in param_optimizer if any(nd in n for nd in no_decay)], 'weight_decay_rate': 0.0}
            ]
        t_total = num_train_steps
#     print(t_total)
    if local_rank != -1:
        t_total = t_total // torch.distributed.get_world_size()
    if do_train:
        optimizer = BertAdam(optimizer_grouped_parameters,
                         lr=learning_rate,
                         warmup=warmup_proportion,
                         t_total=t_total)

    global_step = 0
    if do_train:

        claim_features = convert_claims_to_features(train_examples, label_list, max_seq_length, tokenizer)
        train_features = convert_pers_to_features(train_examples, label_list, max_seq_length, tokenizer)
        logger.info("perspective features done")
        opposite_claim_features = convert_opp_claims_to_features(train_examples, label_list, max_seq_length, tokenizer)
        logger.info("opposite claim features done")
        opposite_perspective_features = convert_opp_pers_to_features(train_examples, label_list, max_seq_length, tokenizer)

        logger.info("***** Running training *****")
        logger.info("  Num examples = %d", len(train_examples))
        logger.info("  Batch size = %d", train_batch_size)
        logger.info("  Num steps = %d", num_train_steps)
        
            
        pers_input_ids = torch.tensor([f.input_ids for f in train_features], dtype=torch.long)
        pers_input_mask = torch.tensor([f.input_mask for f in train_features], dtype=torch.long)
        pers_segment_ids = torch.tensor([f.segment_ids for f in train_features], dtype=torch.long)
        pers_label_ids = torch.tensor([f.label_id for f in train_features], dtype=torch.long)

        claims_input_ids = torch.tensor([f.input_ids for f in claim_features], dtype=torch.long)
        claims_input_mask = torch.tensor([f.input_mask for f in claim_features], dtype=torch.long)
        claims_segment_ids = torch.tensor([f.segment_ids for f in claim_features], dtype=torch.long)
        claims_label_ids = torch.tensor([f.label_id for f in claim_features], dtype=torch.long)
        
        
        opp_pers_input_ids = torch.tensor([f.input_ids for f in opposite_perspective_features], dtype=torch.long)
        opp_pers_input_mask = torch.tensor([f.input_mask for f in opposite_perspective_features], dtype=torch.long)
        opp_pers_segment_ids = torch.tensor([f.segment_ids for f in opposite_perspective_features], dtype=torch.long)
        opp_pers_label_ids = torch.tensor([f.label_id for f in opposite_perspective_features], dtype=torch.long)
        
        
#         opp_pers_input_ids = torch.tensor([f.input_ids for f in opposite_perspective_features if f.input_ids], dtype=torch.long)
#         opp_pers_input_mask = torch.tensor([f.input_mask for f in opposite_perspective_features if f.input_mask], dtype=torch.long)
#         opp_pers_segment_ids = torch.tensor([f.segment_ids for f in opposite_perspective_features if f.segment_ids], dtype=torch.long)
#         opp_pers_label_ids = torch.tensor([f.label_id for f in opposite_perspective_features if f.label_id], dtype=torch.long)

        opp_claims_input_ids = torch.tensor([f.input_ids for f in opposite_claim_features], dtype=torch.long)
        opp_claims_input_mask = torch.tensor([f.input_mask for f in opposite_claim_features], dtype=torch.long)
        opp_claims_segment_ids = torch.tensor([f.segment_ids for f in opposite_claim_features], dtype=torch.long)
        opp_claims_label_ids = torch.tensor([f.label_id for f in opposite_claim_features], dtype=torch.long)
        
#         logger.info("  opp pers id: %d, opp pers mask: %d, opp pers seg: %d, opp pers label: %d, opp calims label: %d, calims label: %d ", len(opp_pers_input_ids),len(opp_pers_input_mask),len(opp_pers_segment_ids),len(opp_pers_label_ids),len(opp_claims_label_ids),len(claims_label_ids))
        
        train_data = TensorDataset(pers_input_ids, pers_input_mask, pers_segment_ids, pers_label_ids, claims_input_ids, claims_input_mask, claims_segment_ids, claims_label_ids, opp_pers_input_ids, opp_pers_input_mask, opp_pers_segment_ids, opp_pers_label_ids, opp_claims_input_ids, opp_claims_input_mask, opp_claims_segment_ids, opp_claims_label_ids)

        if local_rank == -1:
            train_sampler = RandomSampler(train_data)
        else:
            train_sampler = DistributedSampler(train_data)
        train_dataloader = DataLoader(train_data, sampler=train_sampler, batch_size=train_batch_size)

        model.train()

        for _ in trange(int(num_train_epochs), desc="Epoch"):
            tr_loss = 0
            nb_tr_examples, nb_tr_steps = 0, 0
            for step, batch in enumerate(tqdm(train_dataloader, desc="Iteration")):
                batch = tuple(t.to(device) for t in batch)
                input_ids, input_mask, segment_ids, label_ids, claim_input_ids, claim_input_mask, claim_segment_ids, claim_label_ids, opp_input_ids, opp_input_mask, opp_segment_ids, opp_label_ids, opp_claim_input_ids, opp_claim_input_mask, opp_claim_segment_ids, opp_claim_label_ids = batch
                
                out_results = model(input_ids=input_ids, token_type_ids=segment_ids, attention_mask=input_mask, labels=label_ids, input_ids2=claim_input_ids, token_type_ids2=claim_segment_ids, attention_mask2=claim_input_mask, labels2=claim_label_ids, input_ids3=opp_input_ids, token_type_ids3=opp_segment_ids, attention_mask3=opp_input_mask, labels3=opp_label_ids, input_ids4=opp_claim_input_ids, token_type_ids4=opp_claim_segment_ids, attention_mask4=opp_claim_input_mask, labels4=opp_claim_label_ids)
#                 loss = model(input_ids, segment_ids, input_mask, label_ids)
#                 print("out_results:")
#                 print(out_results)
                loss = out_results
            
                if n_gpu > 1:
                    loss = loss.mean() # mean() to average on multi-gpu.
                if fp16 and loss_scale != 1.0:
                    # rescale loss for fp16 training
                    # see https://docs.nvidia.com/deeplearning/sdk/mixed-precision-training/index.html
                    loss = loss * loss_scale
                if gradient_accumulation_steps > 1:
                    loss = loss / gradient_accumulation_steps
                loss.backward()
                tr_loss += loss.item()
                nb_tr_examples += input_ids.size(0)
                nb_tr_steps += 1
                if (step + 1) % gradient_accumulation_steps == 0:
                    if fp16 or optimize_on_cpu:
                        if fp16 and loss_scale != 1.0:
                            # scale down gradients for fp16 training
                            for param in model.parameters():
                                if param.grad is not None:
                                    param.grad.data = param.grad.data / loss_scale
                        is_nan = set_optimizer_params_grad(param_optimizer, model.named_parameters(), test_nan=True)
                        if is_nan:
                            logger.info("FP16 TRAINING: Nan in gradients, reducing loss scaling")
                            loss_scale = loss_scale / 2
                            model.zero_grad()
                            continue
                        optimizer.step()
                        copy_optimizer_params_to_model(model.named_parameters(), param_optimizer)
                    else:
                        optimizer.step()
                    model.zero_grad()
                    global_step += 1

        torch.save(model.state_dict(), output_dir +"neg_siamese_bert_epoch5.pth")


    if do_eval and (local_rank == -1 or torch.distributed.get_rank() == 0):
     
    
        test_df = processor.get_dev_df(data_dir)
        
        new_test_df = generate_opp_dataset(test_df)
        
        new_test_df.to_csv(os.path.join(data_dir, "new_dev.tsv"),sep='\t',index=False)

        eval_examples = processor.get_test_examples(data_dir)
#         eval_examples = processor.get_dev_examples(data_dir)
        claim_features = convert_claims_to_features(eval_examples, label_list, max_seq_length, tokenizer)
        eval_features = convert_pers_to_features(eval_examples, label_list, max_seq_length, tokenizer)
        
        opposite_claim_features = convert_opp_claims_to_features(eval_examples, label_list, max_seq_length, tokenizer)
        opposite_eval_features = convert_opp_pers_to_features(eval_examples, label_list, max_seq_length, tokenizer)
            
    
        logger.info("***** Running evaluation *****")
        logger.info("  Num examples = %d", len(eval_examples))
        logger.info("  Batch size = %d", eval_batch_size)
        
        pers_input_ids = torch.tensor([f.input_ids for f in eval_features], dtype=torch.long)
        pers_input_mask = torch.tensor([f.input_mask for f in eval_features], dtype=torch.long)
        pers_segment_ids = torch.tensor([f.segment_ids for f in eval_features], dtype=torch.long)
        pers_label_ids = torch.tensor([f.label_id for f in eval_features], dtype=torch.long)
        
        claims_input_ids = torch.tensor([f.input_ids for f in claim_features], dtype=torch.long)
        claims_input_mask = torch.tensor([f.input_mask for f in claim_features], dtype=torch.long)
        claims_segment_ids = torch.tensor([f.segment_ids for f in claim_features], dtype=torch.long)
        claims_label_ids = torch.tensor([f.label_id for f in claim_features], dtype=torch.long)
        
        opp_pers_input_ids = torch.tensor([f.input_ids for f in opposite_eval_features], dtype=torch.long)
        opp_pers_input_mask = torch.tensor([f.input_mask for f in opposite_eval_features], dtype=torch.long)
        opp_pers_segment_ids = torch.tensor([f.segment_ids for f in opposite_eval_features], dtype=torch.long)
        opp_pers_label_ids = torch.tensor([f.label_id for f in opposite_eval_features], dtype=torch.long)
        
        opp_claims_input_ids = torch.tensor([f.input_ids for f in opposite_claim_features], dtype=torch.long)
        opp_claims_input_mask = torch.tensor([f.input_mask for f in opposite_claim_features], dtype=torch.long)
        opp_claims_segment_ids = torch.tensor([f.segment_ids for f in opposite_claim_features], dtype=torch.long)
        opp_claims_label_ids = torch.tensor([f.label_id for f in opposite_claim_features], dtype=torch.long)
        
        eval_data = TensorDataset(pers_input_ids, pers_input_mask, pers_segment_ids, pers_label_ids, claims_input_ids, claims_input_mask, claims_segment_ids, claims_label_ids, opp_pers_input_ids, opp_pers_input_mask, opp_pers_segment_ids, opp_pers_label_ids, opp_claims_input_ids, opp_claims_input_mask, opp_claims_segment_ids, opp_claims_label_ids)
        # Run prediction for full data
#         eval_sampler = SequentialSampler(eval_data)
        eval_sampler = SequentialSampler(eval_data)
        eval_dataloader = DataLoader(eval_data, sampler=eval_sampler, batch_size=eval_batch_size)
#         print('all_input_ids:')
#         print(all_input_ids)
        
        

#         model.load_state_dict(torch.load(saved_model))
        model_state_dict = torch.load(saved_model)
        model = BertForConsistencyCueClassification.from_pretrained('bert-base-uncased', num_labels=2, state_dict=model_state_dict)
        model.to(device)
        
        model.eval()
        # eval_loss, eval_accuracy = 0, 0

        eval_tp, eval_pred_c, eval_gold_c = 0, 0, 0
        eval_loss, eval_macro_p, eval_macro_r = 0, 0, 0

        raw_score = []

        nb_eval_steps, nb_eval_examples = 0, 0
        for input_ids, input_mask, segment_ids, label_ids, claim_input_ids, claim_input_mask, claim_segment_ids, claim_label_ids, opp_input_ids, opp_input_mask, opp_segment_ids, opp_label_ids, opp_claim_input_ids, opp_claim_input_mask, opp_claim_segment_ids, opp_claim_label_ids in eval_dataloader:
            
            input_ids = input_ids.to(device)
            input_mask = input_mask.to(device)
            segment_ids = segment_ids.to(device)
            label_ids = label_ids.to(device)
            
            claim_input_ids = claim_input_ids.to(device)
            claim_input_mask = claim_input_mask.to(device)
            claim_segment_ids = claim_segment_ids.to(device)
            claim_label_ids = claim_label_ids.to(device)
            
            opp_input_ids = opp_input_ids.to(device)
            opp_input_mask = opp_input_mask.to(device)
            opp_segment_ids = opp_segment_ids.to(device)
            opp_label_ids = opp_label_ids.to(device)
            
            opp_claim_input_ids = opp_claim_input_ids.to(device)
            opp_claim_input_mask = opp_claim_input_mask.to(device)
            opp_claim_segment_ids = opp_claim_segment_ids.to(device)
            opp_claim_label_ids = opp_claim_label_ids.to(device)

#             print("start")
#             print(input_ids)
#             print(input_mask)
#             print(segment_ids)
#             print(label_ids)
#             print(claim_input_ids)
#             print(claim_input_mask)
#             print(claim_segment_ids)
#             print(claim_label_ids)
#             print("end")
            with torch.no_grad():
                tmp_eval_loss = model(input_ids=input_ids, token_type_ids=segment_ids, attention_mask=input_mask, labels=label_ids, input_ids2=claim_input_ids, token_type_ids2=claim_segment_ids, attention_mask2=claim_input_mask, labels2=claim_label_ids, input_ids3=opp_input_ids, token_type_ids3=opp_segment_ids, attention_mask3=opp_input_mask, labels3=opp_label_ids, input_ids4=opp_claim_input_ids, token_type_ids4=opp_claim_segment_ids, attention_mask4=opp_claim_input_mask, labels4=opp_claim_label_ids)
                
                logits = model(input_ids=input_ids, token_type_ids=segment_ids, attention_mask=input_mask, input_ids2=claim_input_ids, token_type_ids2=claim_segment_ids, attention_mask2=claim_input_mask, input_ids3=opp_input_ids, token_type_ids3=opp_segment_ids, attention_mask3=opp_input_mask, input_ids4=opp_claim_input_ids, token_type_ids4=opp_claim_segment_ids, attention_mask4=opp_claim_input_mask)
            
#             print(logits)
#             print(logits[0])
            logits = logits.detach().cpu().numpy()
#             print(logits)
            label_ids = label_ids.to('cpu').numpy()
#             print(label_ids)

            # Micro F1 (aggregated tp, fp, fn counts across all examples)
            tmp_tp, tmp_pred_c, tmp_gold_c = tp_pcount_gcount(logits, label_ids)
            eval_tp += tmp_tp
            eval_pred_c += tmp_pred_c
            eval_gold_c += tmp_gold_c
            
            pred_label = np.argmax(logits, axis=1)
            raw_score += zip(logits, pred_label, label_ids)
            
            # Macro F1 (averaged P, R across mini batches)
            tmp_eval_p, tmp_eval_r, tmp_eval_f1 = p_r_f1(logits, label_ids)

            eval_macro_p += tmp_eval_p
            eval_macro_r += tmp_eval_r

            eval_loss += tmp_eval_loss.mean().item()
            nb_eval_examples += input_ids.size(0)
            nb_eval_steps += 1


        # Micro F1 (aggregated tp, fp, fn counts across all examples)
        eval_micro_p = eval_tp / eval_pred_c
        eval_micro_r = eval_tp / eval_gold_c
        eval_micro_f1 = 2 * eval_micro_p * eval_micro_r / (eval_micro_p + eval_micro_r)

        # Macro F1 (averaged P, R across mini batches)
        eval_macro_p = eval_macro_p / nb_eval_steps
        eval_macro_r = eval_macro_r / nb_eval_steps
        eval_macro_f1 = 2 * eval_macro_p * eval_macro_r / (eval_macro_p + eval_macro_r)

        eval_loss = eval_loss / nb_eval_steps
        result = {
                  'eval_loss': eval_loss,
                  'eval_micro_p': eval_micro_p,
                  'eval_micro_r': eval_micro_r,
                  'eval_micro_f1': eval_micro_f1,
                  'eval_macro_p': eval_macro_p,
                  'eval_macro_r': eval_macro_r,
                  'eval_macro_f1': eval_macro_f1,
#                   'global_step': global_step,
#                   'loss': tr_loss/nb_tr_steps
                  }

        output_eval_file = os.path.join(output_dir, "neg_siamese_bert_epoch5_eval_results.txt")
        output_raw_score = os.path.join(output_dir, "neg_siamese_bert_epoch5_raw_score.csv")
        with open(output_eval_file, "w") as writer:
            logger.info("***** Eval results *****")
            for key in sorted(result.keys()):
                logger.info("  %s = %s", key, str(result[key]))
                writer.write("%s = %s\n" % (key, str(result[key])))

        with open(output_raw_score, 'w') as fout:
            fields = ["undermine_score", "support_score","predict_label", "gold"]
            writer = csv.DictWriter(fout, fieldnames=fields)
            writer.writeheader()
            for score, pred, gold in raw_score:
                writer.writerow({
                    "undermine_score": str(score[0]),
                    "support_score": str(score[1]),
                    "predict_label": str(pred),
                    "gold": str(gold)
                })


# In[ ]:





# In[ ]:


def experiments():
    data_dir = "/var/scratch/syg340/project/stance_code/Dataset"
#     data_dir = "/var/scratch/syg340/project/stance_code/Dataset/stancy/"
#     data_dir = "/var/scratch/syg340/project/stance_code/Dataset/ibmcs/"
    
    
#     data_dir_output = "/var/scratch/syg340/project/cos_siamese_models/siamese_ibmcs/"
    data_dir_output = "/var/scratch/syg340/project/stance_code/Evaluation/319/"
    train_and_test(data_dir=data_dir, do_train=True, do_eval=False, output_dir=data_dir_output,task_name="neg")


# In[10]:


def evaluation_with_pretrained():
#     bert_model = "/var/scratch/syg340/project/cos_siamese_models/319cos/319_cos_camimu_siamese_bert_epoch5.pth"
    bert_model = "/var/scratch/syg340/project/stance_code/Evaluation/319/neg_siamese_bert_epoch5.pth"
    data_dir = "/var/scratch/syg340/project/stance_code/Dataset"
#     data_dir = "/var/scratch/syg340/project/stance_code/Dataset/ibmcs/"

    data_dir_output = "/var/scratch/syg340/project/stance_code/Evaluation/bert_dummy_output/"
    train_and_test(data_dir=data_dir, do_train=False, do_eval=True, output_dir=data_dir_output,task_name="neg",saved_model=bert_model)


# In[11]:


if __name__ == "__main__":
#     experiments()
    evaluation_with_pretrained()


# In[ ]:




