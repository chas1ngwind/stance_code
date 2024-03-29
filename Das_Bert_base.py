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


from run_classifier import StanceProcessor, MrpcProcessor, logger, convert_examples_to_features,    set_optimizer_params_grad, copy_optimizer_params_to_model, accuracy, p_r_f1, tp_pcount_gcount, convert_claims_to_features, convert_pers_to_features


# In[11]:


if torch.cuda.is_available():    

    # Tell PyTorch to use the GPU.    
    device = torch.device("cuda")
    n_gpu = torch.cuda.device_count()
    logger.info('There are %d GPU(s) available.' % (n_gpu))
    logger.info('We will use the GPU:')
    logger.info(torch.cuda.get_device_name(0))

# If not...
else:
    logger.info('No GPU available, using the CPU instead.')
    device = torch.device("cpu")

from transformers import BertTokenizer, AdamW, get_linear_schedule_with_warmup
from pytorch_pretrained_bert.modeling import BertForSequenceClassification, BertPreTrainedModel, BertModel, BertConfig
from torch.nn import BCEWithLogitsLoss, CosineEmbeddingLoss,CrossEntropyLoss, MSELoss

import csv
from pytorch_pretrained_bert.file_utils import PYTORCH_PRETRAINED_BERT_CACHE
def train_and_test(data_dir, bert_model="bert-base-uncased", task_name=None,
                   output_dir=None, max_seq_length=128, do_train=False, do_eval=False, do_lower_case=False,
                   train_batch_size=32, eval_batch_size=8, learning_rate=2e-5, num_train_epochs=4,
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
        "stance":StanceProcessor
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
#             raise ValueError("Output directory ({}) already exists and is not emp1ty.".format(output_dir))
        os.makedirs(output_dir, exist_ok=True)

    task_name = task_name.lower()

    if task_name not in processors:
        raise ValueError("Task not found: %s" % (task_name))

    processor = processors[task_name]()
    label_list = processor.get_labels()

    tokenizer = BertTokenizer.from_pretrained(bert_model, do_lower_case=do_lower_case)

    train_examples = None
    num_train_steps = None
    if do_train:
        train_examples = processor.get_train_examples(data_dir)
        num_train_steps = int(
            len(train_examples) / train_batch_size / gradient_accumulation_steps * num_train_epochs)

    # Prepare model
    model = BertForSequenceClassification.from_pretrained(bert_model,
                cache_dir=PYTORCH_PRETRAINED_BERT_CACHE / 'distributed_{}'.format(local_rank), num_labels=2)
    if fp16:
        model.half()
    model.to(device)
    if local_rank != -1:
        model = torch.nn.parallel.DistributedDataParallel(model, device_ids=[local_rank],
                                                          output_device=local_rank)
    elif n_gpu > 1:
        model = torch.nn.DataParallel(model)

    # Prepare optimizer
    if fp16:
        param_optimizer = [(n, param.clone().detach().to('cpu').float().requires_grad_()) \
                            for n, param in model.named_parameters()]
    elif optimize_on_cpu:
        param_optimizer = [(n, param.clone().detach().to('cpu').requires_grad_()) \
                            for n, param in model.named_parameters()]
    else:
        param_optimizer = list(model.named_parameters())
    no_decay = ['bias', 'gamma', 'beta']
    optimizer_grouped_parameters = [
        {'params': [p for n, p in param_optimizer if not any(nd in n for nd in no_decay)], 'weight_decay_rate': 0.01},
        {'params': [p for n, p in param_optimizer if any(nd in n for nd in no_decay)], 'weight_decay_rate': 0.0}
        ]
    t_total = num_train_steps
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
            process_bar = tqdm(train_dataloader)
            for step, batch in enumerate(tqdm(train_dataloader, desc="Iteration")):
                batch = tuple(t.to(device) for t in batch)
                input_ids, input_mask, segment_ids, label_ids = batch
                loss = model(input_ids, segment_ids, input_mask, label_ids)
                if n_gpu > 1:
                    loss = loss.mean() # mean() to average on multi-gpu.
                if fp16 and loss_scale != 1.0:
                    # rescale loss for fp16 training
                    # see https://docs.nvidia.com/deeplearning/sdk/mixed-precision-training/index.html
                    loss = loss * loss_scale
                if gradient_accumulation_steps > 1:
                    loss = loss / gradient_accumulation_steps
                process_bar.set_description("Loss: %0.8f" % (loss.sum().item()))
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
            print("\nLoss: {}\n".format(tr_loss / nb_tr_steps))
        torch.save(model.state_dict(), output_dir + "train_on_reverse_perspectrum_bert_base_bs32_lr2e_5_epoch4.pth")


    if do_eval and (local_rank == -1 or torch.distributed.get_rank() == 0):
        eval_examples = processor.get_test_examples(data_dir)
#         eval_examples = processor.get_dev_examples(data_dir)
        eval_features = convert_examples_to_features(
            eval_examples, label_list, max_seq_length, tokenizer)
        logger.info("***** Running evaluation *****")
        logger.info("  Num examples = %d", len(eval_examples))
        logger.info("  Batch size = %d", eval_batch_size)
        all_input_ids = torch.tensor([f.input_ids for f in eval_features], dtype=torch.long)
        all_input_mask = torch.tensor([f.input_mask for f in eval_features], dtype=torch.long)
        all_segment_ids = torch.tensor([f.segment_ids for f in eval_features], dtype=torch.long)
        all_label_ids = torch.tensor([f.label_id for f in eval_features], dtype=torch.long)
        eval_data = TensorDataset(all_input_ids, all_input_mask, all_segment_ids, all_label_ids)
        # Run prediction for full data
        eval_sampler = SequentialSampler(eval_data)
        eval_dataloader = DataLoader(eval_data, sampler=eval_sampler, batch_size=eval_batch_size)

        model.load_state_dict(torch.load(saved_model))

#         model.eval()        
        

# #         model.load_state_dict(torch.load(saved_model))
#         model_state_dict = torch.load(saved_model)
#         model = BertForConsistencyCueClassification.from_pretrained('bert-base-uncased', num_labels=2, state_dict=model_state_dict)
        model.to(device)
        
        model.eval()
        # eval_loss, eval_accuracy = 0, 0

        eval_tp, eval_pred_c, eval_gold_c = 0, 0, 0
        eval_loss, eval_macro_p, eval_macro_r = 0, 0, 0

        raw_score = []

        nb_eval_steps, nb_eval_examples = 0, 0
        for input_ids, input_mask, segment_ids, label_ids in eval_dataloader:
            input_ids = input_ids.to(device)
            input_mask = input_mask.to(device)
            segment_ids = segment_ids.to(device)
            label_ids = label_ids.to(device)

            with torch.no_grad():
                tmp_eval_loss = model(input_ids, segment_ids, input_mask, label_ids)
                logits = model(input_ids, segment_ids, input_mask)

            logits = logits.detach().cpu().numpy()
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

        output_eval_file = os.path.join(output_dir, "train_on_reverse_perspectrum_bert_base_eval_results.txt")
        output_raw_score = os.path.join(output_dir, "train_on_reverse_perspectrum_bert_base_raw_score.csv")
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
#     bert_model = "/var/scratch/syg340/project/models/bert_base_bs32_lr2e_5_epoch4.pth"
    bert_model = "/var/scratch/syg340/project/models/train_on_reverse_perspectrum_bert_base_bs32_lr2e_5_epoch4.pth"
#     data_dir = "/var/scratch/syg340/project/stance_code/Dataset"
    data_dir = "/var/scratch/syg340/project/stance_code/Dataset/reverse_perspectrum/"
#     data_dir = "/var/scratch/syg340/project/stance_code/Dataset/naive_opposite/subset/"
#     data_dir = "/var/scratch/syg340/project/stance_code/Dataset/manul_opposite/500_gold0/"

    data_dir_output = "/var/scratch/syg340/project/stance_code/Evaluation/antonym_output/"
    train_and_test(data_dir=data_dir, do_train=False, do_eval=True, output_dir=data_dir_output,task_name="stance",saved_model=bert_model)

# In[11]:


if __name__ == "__main__":
#     experiments()
    evaluation_with_pretrained()


# In[ ]:




