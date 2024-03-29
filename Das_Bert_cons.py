#!/usr/bin/env python
# coding: utf-8

# In[1]:


import torch
import random
import numpy as np
import os

from tqdm import tqdm, trange
# torch.cuda.empty_cache()
from torch.utils.data import TensorDataset, DataLoader, RandomSampler, SequentialSampler
from pytorch_pretrained_bert.optimization import BertAdam
# from pytorch_pretrained_bert.tokenization import BertTokenizer, WordpieceTokenizer


# In[2]:


from run_classifier import StanceProcessor, ColaProcessor, MrpcProcessor, logger, convert_examples_to_features,    set_optimizer_params_grad, copy_optimizer_params_to_model, accuracy, p_r_f1, tp_pcount_gcount, convert_claims_to_features


# In[3]:


if torch.cuda.is_available():    

    # Tell PyTorch to use the GPU.    
    device = torch.device("cuda")
    n_gpu = torch.cuda.device_count()
#     device = torch.device("cpu")
    print('There are %d GPU(s) available.' % n_gpu)

    print('We will use the GPU:', torch.cuda.get_device_name(0))

# If not...
else:
    print('No GPU available, using the CPU instead.')
    device = torch.device("cpu")


# In[4]:


from transformers import BertTokenizer, AdamW, get_linear_schedule_with_warmup
from pytorch_pretrained_bert.modeling import BertForSequenceClassification, BertPreTrainedModel, BertModel, BertConfig
from torch.nn import BCEWithLogitsLoss, CosineEmbeddingLoss,CrossEntropyLoss, MSELoss


# In[5]:


# import logging
# logging.basicConfig(level=logging.INFO)


# In[6]:


# def train_and_test(data_dir, bert_model="bert-base-uncased", task_name=None,
#                    output_dir=None, max_seq_length=128, do_train=False, do_eval=False, do_lower_case=False,
#                    train_batch_size=32, eval_batch_size=8, learning_rate=5e-5, num_train_epochs=3,
#                    warmup_proportion=0.1,no_cuda=False, local_rank=-1, seed=42, gradient_accumulation_steps=1,
#                    optimize_on_cpu=False, fp16=False, loss_scale=128, saved_model=""):


# In[ ]:





# In[11]:


class BertForConsistencyCueClassification(BertPreTrainedModel):
    def __init__(self, config, num_labels=2):
        super(BertForConsistencyCueClassification, self).__init__(config)
        self.num_labels = num_labels

        self.bert = BertModel(config)
        self.dropout = torch.nn.Dropout(config.hidden_dropout_prob)
        self.classifier = torch.nn.Linear(config.hidden_size+1, num_labels)
        self.classifier2 = torch.nn.Linear(config.hidden_size, num_labels)
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

        _, outputs = self.bert(
            input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
#             position_ids=position_ids,
#             head_mask=head_mask,
#             inputs_embeds=inputs_embeds,
        )

        _, outputsC = self.bert(
            input_ids2,
            attention_mask=attention_mask2,
            token_type_ids=token_type_ids2,
#             position_ids=position_ids2,
#             head_mask=head_mask2,
#             inputs_embeds=inputs_embeds2,
        )
#         print("Careful, outputs:")
#         print(outputs)
#         print(outputsC)
        pooled_output = outputs
        pooled_outputC = outputsC

        pooled_output = self.dropout(pooled_output)
#         pooled_outputC = self.dropout(pooled_outputC)
        
        cos_pooled_outputs = torch.cosine_similarity(pooled_output, pooled_outputC, dim=1)
        
#         print('pooled_output size:')
#         print(pooled_output.size())
#         print(pooled_output)
#         print('cos_pooled_outputs size:')
#         print(cos_pooled_outputs.size())
#         print(cos_pooled_outputs)
        batch_size = list(pooled_output.size())[0]
        hidden_size = list(pooled_output.size())[1]

#         logits_ce = self.classifier2(pooled_outputC)
#         print('logits_ce:')
#         print(logits_ce)
        
    
        ## v2: concat
        ## v3: multiply
        ## v4: v2 & ce_cos_similarity
        ## v5: v3 & ce_cos_similarity
        
#         print(torch.cat((pooled_output, cos_pooled_outputs.unsqueeze(1)),1))
#         print((pooled_output*cos_pooled_outputs.unsqueeze(1)))
        logits_cos = self.classifier(torch.cat((pooled_output, cos_pooled_outputs.unsqueeze(1)),1))
        logits_final = logits_cos
#         logits_cos = self.classifier2((pooled_output*cos_pooled_outputs.unsqueeze(1)))
#         self.classifier = torch.nn.Linear(hidden_size+batch_size, 2).to(device)
#         logits_cos = self.classifier(torch.cat((pooled_output, cos_pooled_outputs.repeat(batch_size,1)),1))
#         print('logits_cos:')
#         print(logits_cos)
        
#         logits = self.classifier(pooled_output)
#         logitsC = self.classifier(pooled_outputC)

#         outputs = (logits,) + outputs[2:]  # add hidden states and attention if they are here
#         print(logits)
#         print('xd')
#         print(outputs[2:])
#         outputs = (logits,) + outputs[2:]
#         print("labels:")
#         print(labels)
        if labels is not None:
            if self.num_labels == 1:
                #  We are doing regression
                loss_fct = MSELoss()
                loss = loss_fct(logits.view(-1), labels.view(-1))
            else:
#                 loss_fct_ce = CrossEntropyLoss()
#                 loss_ce = loss_fct(logits.view(-1, self.num_labels), labels.view(-1))

                loss_fct_ce = CrossEntropyLoss()
#                 print('pooled_output size:')
#                 print(pooled_output.size())
                loss_ce = loss_fct_ce(logits_final.view(-1, self.num_labels), labels.view(-1))
#                 loss_ce = loss_fct_ce(pooled_output.view(-1), labels.view(-1))
#                 print('loss_ce:')
#                 print(loss_ce)

                loss_fct_cos = CosineEmbeddingLoss()
                labels2[labels2==0] = -1
                loss_cos = loss_fct_cos(pooled_output, pooled_outputC, labels2)
                labels2[labels2==-1] = 0
                
#                 loss_fct_cos = CosineEmbeddingLoss()
# #                 print(labels)
# #                 print(pooled_outputC)


# #                 labels2[labels2==0] = -1
#                 loss_cos = loss_fct_cos(pooled_output, pooled_outputC, labels2)
        
        
#                 loss_cos = loss_fct_cos(logits_ce, logits_cos, labels2)
#                 loss_cos = loss_fct_ce(logits_cos.view(-1, self.num_labels), labels2.view(-1))
#                 print('loss_cos:')
#                 print(loss_cos)
            
                loss = loss_cos+loss_ce
#                 print('final loss:')
#                 print(loss)
#                 logits = self.classifier(loss)
#             outputs = (loss,) + outputs
#             outputs = (loss,) + logits_cos 
                outputs = loss
                return outputs
        else:
            return logits_final
        
          # (loss), logits, (hidden_states), (attentions)


# In[ ]:





# In[8]:


# labe = torch.ones(8)
# print(labe )
# labe[labe==1] = -1
# labe


# In[9]:


# a = torch.tensor([[4.2,5,6,7,8],[9,10,11,12,13]])
# b = torch.tensor([[3.4,5,6,7,8],[9,10,11,12,13]])

# # a = torch.tensor([[4,5,6,7,8],[9,10,11,12,13]])
# # b = torch.tensor([1,2])
# c= torch.cosine_similarity(a,b,dim=1)
# # b.unsqueeze(1)
# # # a.size()
# # torch.cat((a,c.unsqueeze(1)),1)
# a*c.unsqueeze(1)


# In[10]:


# input1 = torch.randn(100, 128)
# input2 = torch.randn(100, 128)
# output = torch.cosine_similarity(input1, input2, dim=1)


# In[ ]:

# #####################Comment From Here###############################################



# In[11]:


tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')


# In[12]:


# Prepare model 
model = BertForConsistencyCueClassification.from_pretrained('bert-base-uncased', num_labels=2)
model.to(device)

# model = BertModel.from_pretrained('bert-base-uncased')


# # In[13]:


# # Get all of the model's parameters as a list of tuples.
# params = list(model.named_parameters())

# # print('The BERT model has {:} different named parameters.\n'.format(len(params)))

# # print('==== Embedding Layer ====\n')

# # for p in params[0:5]:
# #     print("{:<55} {:>12}".format(p[0], str(tuple(p[1].size()))))

# # print('\n==== First Transformer ====\n')

# # for p in params[5:21]:
# #     print("{:<55} {:>12}".format(p[0], str(tuple(p[1].size()))))
    
# # print('\n==== Output Layer ====\n')

# # for p in params[-4:]:
# #     print("{:<55} {:>12}".format(p[0], str(tuple(p[1].size()))))


# # In[14]:


# data_dir = "D:/Jupyter/data/dataset/perspective_stances/"
# data_dir = "D:/Projects/Stance/Dataset/BertForOppositeClassification/"
# # data_dir_output = "D:/Projects/Stance/Models/Consistency_Cues/"
# data_dir_output = "D:/Projects/Stance/Models/dataExpantion/"
# data_dir = "/var/scratch/syg340/project/stance_code/Dataset/"
data_dir = "/var/scratch/syg340/project/stance_code/Dataset/reverse_perspectrum/"
    
data_dir_output = "/var/scratch/syg340/project/models/"
output_dir=data_dir_output
max_seq_length=128
max_grad_norm = 1.0
num_training_steps = 1000
num_warmup_steps = 100
warmup_proportion = float(num_warmup_steps) / float(num_training_steps)  # 0.1
# warmup_proportion = 0.1
train_batch_size=24
eval_batch_size=8
learning_rate=1e-5
num_train_epochs=15
local_rank=-1
seed=42
gradient_accumulation_steps=1
loss_scale=128
train_batch_size = int(train_batch_size / gradient_accumulation_steps)

processors = {
        "mrpc": MrpcProcessor,
        "stance":StanceProcessor
    }

random.seed(seed)
np.random.seed(seed)
torch.manual_seed(seed)
torch.cuda.manual_seed_all(seed)
    
os.makedirs(output_dir, exist_ok=True)
processor = processors['stance']()
label_list = processor.get_labels()
num_labels = len(label_list)
# print('label list')
# print(label_list)

train_examples = processor.get_train_examples(data_dir)
num_train_steps = int(
    len(train_examples) / train_batch_size / gradient_accumulation_steps * num_train_epochs)

##preprare optimizer
param_optimizer = list(model.named_parameters())
no_decay = ['bias', 'gamma', 'beta']
optimizer_grouped_parameters = [
    {'params': [p for n, p in param_optimizer if not any(nd in n for nd in no_decay)], 'weight_decay_rate': 0.01},
    {'params': [p for n, p in param_optimizer if any(nd in n for nd in no_decay)], 'weight_decay_rate': 0.0}
    ]
t_total = num_train_steps
optimizer = BertAdam(optimizer_grouped_parameters,
                         lr=learning_rate,
                         warmup=warmup_proportion,
                         t_total=t_total)
# optimizer = AdamW(optimizer_grouped_parameters,
#                   lr = learning_rate, # args.learning_rate - default is 5e-5, our notebook had 2e-5
#                   eps = 1e-8, # args.adam_epsilon  - default is 1e-8.
#                   correct_bias=False
#                 )

# scheduler = get_linear_schedule_with_warmup(optimizer, num_warmup_steps=num_warmup_steps, num_training_steps=t_total)  # PyTorch scheduler


# In[15]:


global_step = 0
train_features = convert_examples_to_features(train_examples, label_list, max_seq_length, tokenizer)
claim_features = convert_claims_to_features(train_examples, label_list, max_seq_length, tokenizer)
logger.info("***** Running training *****")
logger.info("  Num examples = %d", len(train_examples))
logger.info("  Batch size = %d", train_batch_size)
logger.info("  Num steps = %d", num_train_steps)


all_input_ids = torch.tensor([f.input_ids for f in train_features], dtype=torch.long)
all_input_mask = torch.tensor([f.input_mask for f in train_features], dtype=torch.long)
all_segment_ids = torch.tensor([f.segment_ids for f in train_features], dtype=torch.long)
all_label_ids = torch.tensor([f.label_id for f in train_features], dtype=torch.long)

claims_input_ids = torch.tensor([f.input_ids for f in claim_features], dtype=torch.long)
claims_input_mask = torch.tensor([f.input_mask for f in claim_features], dtype=torch.long)
claims_segment_ids = torch.tensor([f.segment_ids for f in claim_features], dtype=torch.long)
claims_label_ids = torch.tensor([f.label_id for f in claim_features], dtype=torch.long)

train_data = TensorDataset(all_input_ids, all_input_mask, all_segment_ids, all_label_ids, claims_input_ids, claims_input_mask, claims_segment_ids, claims_label_ids)
train_sampler = RandomSampler(train_data)
train_dataloader = DataLoader(train_data, sampler=train_sampler, batch_size=train_batch_size)

# claims_data = TensorDataset(claims_input_ids, claims_input_mask, claims_segment_ids, claims_label_ids)
# claims_sampler = RandomSampler(claims_data)
# claims_dataloader = DataLoader(claims_data, sampler=train_sampler, batch_size=train_batch_size)


# In[16]:


model.train()
for _ in trange(int(num_train_epochs), desc="Epoch"):
    tr_loss = 0
    nb_tr_examples, nb_tr_steps = 0, 0
    for step, batch in enumerate(tqdm(train_dataloader, desc="Iteration")):
        batch = tuple(t.to(device) for t in batch)
        input_ids, input_mask, segment_ids, label_ids, claim_input_ids, claim_input_mask, claim_segment_ids, claim_label_ids = batch
#         ce_loss = model(input_ids, segment_ids, input_mask, label_ids)
#         cos_loss = model(claim_input_ids, claim_segment_ids, claim_input_mask, claim_label_ids)
        
#         print("start")
#         print(input_ids)
#         print(input_mask)
#         print(segment_ids)
#         print(label_ids)
#         print(claim_input_ids)
#         print(claim_input_mask)
#         print(claim_segment_ids)
#         print(claim_label_ids)
#         print("end")
    
        out_results = model(input_ids=input_ids, token_type_ids=segment_ids, attention_mask=input_mask, labels=label_ids, input_ids2=claim_input_ids, token_type_ids2=claim_segment_ids, attention_mask2=claim_input_mask, labels2=claim_label_ids)
#         loss = ce_loss + cos_loss
#         print("out_results:")
#         print(out_results)
        loss = out_results
#         print(cos_loss)
#         print(loss.item())
        if n_gpu > 1:
            loss = loss.mean() # mean() to average on multi-gpu.
#         if fp16 and loss_scale != 1.0:
#             # rescale loss for fp16 training
#             # see https://docs.nvidia.com/deeplearning/sdk/mixed-precision-training/index.html
#             loss = loss * loss_scale
        if gradient_accumulation_steps > 1:
            loss = loss / gradient_accumulation_steps
        loss.backward()
        
        tr_loss += loss.item()
        nb_tr_examples += input_ids.size(0)
        nb_tr_steps += 1
        if (step + 1) % gradient_accumulation_steps == 0:
#             if fp16 or optimize_on_cpu:
#                 if fp16 and loss_scale != 1.0:
#                     # scale down gradients for fp16 training
#                     for param in model.parameters():
#                         if param.grad is not None:
#                             param.grad.data = param.grad.data / loss_scale           
#                 is_nan = set_optimizer_params_grad(param_optimizer, model.named_parameters(), test_nan=True)
#                 if is_nan:
#                     logger.info("FP16 TRAINING: Nan in gradients, reducing loss scaling")
#                     loss_scale = loss_scale / 2
#                     model.zero_grad()
#                     continue 
#                 optimizer.step()
# #                 scheduler.step()
#                 copy_optimizer_params_to_model(model.named_parameters(), param_optimizer)
#             else:
#                 torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
            optimizer.step()
#                 scheduler.step()
            model.zero_grad()
            global_step += 1

        
## v2: concat
## v3: multiply
model_to_save = model.module if hasattr(model, 'module') else model
torch.save(model.state_dict(), output_dir + "train_on_reverse_perspectrum_non_reverse_bertcons_epoch5.pth")
# torch.save(model_to_save.state_dict(), output_dir + "finetuned_consistencycues_expansion.bin")





# #####################Comment Ends Here###############################################


# In[13]:


import csv
from pytorch_pretrained_bert.file_utils import PYTORCH_PRETRAINED_BERT_CACHE
def train_and_test(data_dir, bert_model="bert-base-uncased", task_name=None,
                   output_dir=None, max_seq_length=128, do_train=False, do_eval=False, do_lower_case=False,
                   train_batch_size=32, eval_batch_size=8, learning_rate=5e-5, num_train_epochs=5,
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
        "stance": StanceProcessor
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
        if os.path.exists(output_dir) and os.listdir(output_dir):
            raise ValueError("Output directory ({}) already exists and is not emp1ty.".format(output_dir))
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
        train_features = convert_examples_to_features(
            train_examples, label_list, max_seq_length, tokenizer)
        logger.info("***** Running training *****")
        logger.info("  Num examples = %d", len(train_examples))
        logger.info("  Batch size = %d", train_batch_size)
        logger.info("  Num steps = %d", num_train_steps)
        all_input_ids = torch.tensor([f.input_ids for f in train_features], dtype=torch.long)
        all_input_mask = torch.tensor([f.input_mask for f in train_features], dtype=torch.long)
        all_segment_ids = torch.tensor([f.segment_ids for f in train_features], dtype=torch.long)
        all_label_ids = torch.tensor([f.label_id for f in train_features], dtype=torch.long)
        train_data = TensorDataset(all_input_ids, all_input_mask, all_segment_ids, all_label_ids)
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
                input_ids, input_mask, segment_ids, label_ids, = batch
                loss = model(input_ids, segment_ids, input_mask, label_ids)
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

        torch.save(model.state_dict(), output_dir + "train_on_reverse_perspectrum_non_reverse_bertcons_epoch5.pth")


    if do_eval and (local_rank == -1 or torch.distributed.get_rank() == 0):
        eval_examples = processor.get_test_examples(data_dir)
#         eval_examples = processor.get_dev_examples(data_dir)
        eval_features = convert_examples_to_features(
            eval_examples, label_list, max_seq_length, tokenizer)
        claim_features = convert_claims_to_features(eval_examples, label_list, max_seq_length, tokenizer)    
    
        logger.info("***** Running evaluation *****")
        logger.info("  Num examples = %d", len(eval_examples))
        logger.info("  Batch size = %d", eval_batch_size)
        all_input_ids = torch.tensor([f.input_ids for f in eval_features], dtype=torch.long)
        all_input_mask = torch.tensor([f.input_mask for f in eval_features], dtype=torch.long)
        all_segment_ids = torch.tensor([f.segment_ids for f in eval_features], dtype=torch.long)
        all_label_ids = torch.tensor([f.label_id for f in eval_features], dtype=torch.long)
        
        claims_input_ids = torch.tensor([f.input_ids for f in claim_features], dtype=torch.long)
        claims_input_mask = torch.tensor([f.input_mask for f in claim_features], dtype=torch.long)
        claims_segment_ids = torch.tensor([f.segment_ids for f in claim_features], dtype=torch.long)
        claims_label_ids = torch.tensor([f.label_id for f in claim_features], dtype=torch.long)
        
        eval_data = TensorDataset(all_input_ids, all_input_mask, all_segment_ids, all_label_ids, claims_input_ids, claims_input_mask, claims_segment_ids, claims_label_ids)
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
        for input_ids, input_mask, segment_ids, label_ids, claim_input_ids, claim_input_mask, claim_segment_ids, claim_label_ids in eval_dataloader:
            input_ids = input_ids.to(device)
            input_mask = input_mask.to(device)
            segment_ids = segment_ids.to(device)
            label_ids = label_ids.to(device)
            claim_input_ids = claim_input_ids.to(device)
            claim_input_mask = claim_input_mask.to(device)
            claim_segment_ids = claim_segment_ids.to(device)
            claim_label_ids = claim_label_ids.to(device)

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
                tmp_eval_loss = model(input_ids=input_ids, token_type_ids=segment_ids, attention_mask=input_mask, labels=label_ids, input_ids2=claim_input_ids, token_type_ids2=claim_segment_ids, attention_mask2=claim_input_mask, labels2=claim_label_ids)
                
                logits = model(input_ids=input_ids, token_type_ids=segment_ids, attention_mask=input_mask, input_ids2=claim_input_ids, token_type_ids2=claim_segment_ids, attention_mask2=claim_input_mask)
            
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

        output_eval_file = os.path.join(output_dir, "train_on_reverse_perspectrum_bert_cons_epoch5_eval_results.txt")
        output_raw_score = os.path.join(output_dir, "train_on_reverse_perspectrum_bert_cons_epoch5_raw_score.csv")
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
#     data_dir = "/var/scratch/syg340/project/stance_code/Dataset"
#     data_dir = "/var/scratch/syg340/project/stance_code/Dataset/"
    data_dir = "/var/scratch/syg340/project/stance_code/Dataset/reverse_perspectrum/"
    
    data_dir_output = "/var/scratch/syg340/project/models/"
#     data_dir_output = "/var/scratch/syg340/project/stance_code/Evaluation/319/"
    train_and_test(data_dir=data_dir, do_train=True, do_eval=False, output_dir=data_dir_output,task_name="stance")


# In[10]:


def evaluation_with_pretrained():
#     bert_model = "/var/scratch/syg340/project/cos_siamese_models/319stancy/319_bertcons_epoch5.pth"
    bert_model = "/var/scratch/syg340/project/models/train_on_reverse_perspectrum_non_reverse_bertcons_epoch5.pth"
#     bertcons_epoch5.pth
#     data_dir = "/var/scratch/syg340/project/stance_code/Dataset"
    data_dir = "/var/scratch/syg340/project/stance_code/Dataset/reverse_perspectrum/"
#     data_dir = "/var/scratch/syg340/project/stance_code/Dataset/tri/"

    data_dir_output = "/var/scratch/syg340/project/stance_code/Evaluation/antonym_output/"
    train_and_test(data_dir=data_dir, do_train=False, do_eval=True, output_dir=data_dir_output,task_name="stance",saved_model=bert_model)


# In[15]:


if __name__ == "__main__":
#     experiments()
    evaluation_with_pretrained()


# In[ ]:




