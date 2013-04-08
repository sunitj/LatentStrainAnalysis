#!/usr/bin/env python

import sys, getopt
import glob, os

JobParams = {
	'HashReads': {
		'outfile': """HashReads_ArrayJob.q""",
		'array': ["""original_reads/""","""*.fastq.*"""],
		'header': ["""#BSUB -J HashReads[1-""","""#BSUB -o PROJECT_HOME/Logs/HashReads-Out-%I.out""","""#BSUB -e PROJECT_HOME/Logs/HashReads-Err-%I.err""","""#BSUB -q medium""","""#BSUB -M 2097152"""],
		'body': ["""sleep ${LSB_JOBINDEX}""","""python hash_fastq_reads.py -r ${LSB_JOBINDEX} -i PROJECT_HOME/original_reads/ -o PROJECT_HOME/hashed_reads/"""]},
	'MergeHash': {
		'outfile': """MergeHash_ArrayJob.q""",
		'array': ["""original_reads/""","""*.fastq"""],
		'header': ["""#BSUB -J JobName[1-""","""#BSUB -o PROJECT_HOME/Logs/MergeHash-Out-%I.out""","""#BSUB -e PROJECT_HOME/Logs/MergeHash-Err-%I.err""","""#BSUB -q medium""","""#BSUB -M 2097152"""],
		'body': ["""sleep ${LSB_JOBINDEX}""","""python merge_hashq_files.py -r ${LSB_JOBINDEX} -i PROJECT_HOME/hashed_reads/ -o PROJECT_HOME/hashed_reads/"""]},
	'GlobalWeights': {
		'outfile': """GlobalWeights_Job.q""",
		'header': ["""#BSUB -J GlobalWeights""","""#BSUB -o PROJECT_HOME/Logs/GlobalWeights-Out.out""","""#BSUB -e PROJECT_HOME/Logs/GlobalWeights-Err.err""","""#BSUB -q medium""","""#BSUB -W 47:10""","""#BSUB -R 'rusage[mem=24192]'""","""#BSUB -M 24097152"""],
		'body': ["""python tfidf_corpus.py -i PROJECT_HOME/hashed_reads/ -o PROJECT_HOME/cluster_vectors/"""]},
	'KmerCorpus': {
		'outfile': """KmerCorpus_ArrayJob.q""",
		'array': ["""hashed_reads/""","""*.count.hash"""],
		'header': ["""#BSUB -J JobName[1-""","""#BSUB -o PROJECT_HOME/Logs/KmerCorpus-Out-%I.out""","""#BSUB -e PROJECT_HOME/Logs/KmerCorpus-Err-%I.err""","""#BSUB -q medium""","""#BSUB -M 12097152"""],
		'body': ["""sleep ${LSB_JOBINDEX}""","""python kmer_corpus.py -r ${LSB_JOBINDEX} -i PROJECT_HOME/hashed_reads/ -o PROJECT_HOME/cluster_vectors/"""]},
	'LSIKmerClusters': {
		'outfile': """LSIKmerClusters_Job.q""",
		'header': ["""#BSUB -J LSIKmerClusters""","""#BSUB -o PROJECT_HOME/Logs/LSIKmerClusters-Out.out""","""#BSUB -e PROJECT_HOME/Logs/LSIKmerClusters-Err.err""","""#BSUB -q medium""","""#BSUB -W 47:10""","""#BSUB -R 'rusage[mem=122192]'""","""#BSUB -M 132097152""","""python -m Pyro4.naming -n 0.0.0.0 > PROJECT_HOME/Logs/nameserver.log 2>&1 &""","""P1=$!""","""python -m gensim.models.lsi_worker > PROJECT_HOME/Logs/worker1.log 2>&1 &""","""P2=$!""","""python -m gensim.models.lsi_worker > PROJECT_HOME/Logs/worker2.log 2>&1 &""","""P3=$!""","""python -m gensim.models.lsi_worker > PROJECT_HOME/Logs/worker3.log 2>&1 &""","""P4=$!""","""python -m gensim.models.lsi_worker > PROJECT_HOME/Logs/worker4.log 2>&1 &""","""P5=$!""","""python -m gensim.models.lsi_worker > PROJECT_HOME/Logs/worker5.log 2>&1 &""","""P6 = $!""","""python -m gensim.models.lsi_dispatcher > PROJECT_HOME/Logs/dispatcher.log 2>&1 &""","""P7 = $!"""],
		'body': ["""python kmer_lsi_clusters.py -i PROJECT_HOME/hashed_reads/ -o PROJECT_HOME/cluster_vectors/""","""kill P1 P2 P3 P4 P5 P6 P7"""]},
	'ReadPartitions': {
		'outfile': """ReadPartitions_ArrayJob.q""",
		'array': ["""hashed_reads/""","""*.hashq.*"""],
		'header': ["""#BSUB -J ReadPartitions[1-""","""#BSUB -o PROJECT_HOME/Logs/ReadPartitions-Out-%I.out""","""#BSUB -e PROJECT_HOME/Logs/ReadPartitions-Err-%I.err""","""#BSUB -q medium""","""#BSUB -W 47:10""","""#BSUB -R 'rusage[mem=12192]'""","""#BSUB -M 12097152"""],
		'body': ["""sleep ${LSB_JOBINDEX}""","""python intermediate_read_clusters.py -r ${LSB_JOBINDEX} -i PROJECT_HOME/hashed_reads/ -o PROJECT_HOME/cluster_vectors/"""]},
	'MergeIntermediatePartitions': {
		'outfile': """MergeIntermediatePartitions_ArrayJob.q""",
		'array': ["""hashed_reads/""","""*.hashq.*"""],
		'header': ["""#BSUB -J MergeIntermediatePartitions[1-""","""#BSUB -o PROJECT_HOME/Logs/MergeIntermediatePartitions-Out-%I.out""","""#BSUB -e PROJECT_HOME/Logs/MergeIntermediatePartitions-Err-%I.err""","""#BSUB -q medium""","""#BSUB -W 47:10""","""#BSUB -R 'rusage[mem=32192]'""","""#BSUB -M 32097152"""],
		'body': ["""sleep ${LSB_JOBINDEX}""","""python merge_read_clusters.py -r ${LSB_JOBINDEX} -i PROJECT_HOME/cluster_vectors/intermediate_clusters/ -o PROJECT_HOME/read_partitions/ -H PROJECT_HOME/hashed_reads/"""]}
}

CommonElements = {
	'header': ["""#!/bin/bash"""],
	'body': ["""cd /import/analysis/comp_bio/metagenomics/latent_strain_analysis""","""echo Date: `date`""","""t1=`date +%s`"""],
	'footer': ["""[ $? -eq 0 ] || echo 'JOB FAILURE: $?'""","""echo Date: `date`""","""t2=`date +%s`""","""tdiff=`echo 'scale=3;('$t2'-'$t1')/3600' | bc`""","""echo 'Total time:  '$tdiff' hours'"""]
}
					
help_message = 'usage example: python create_jobs.py -j HashReads -i /project/home/'
if __name__ == "__main__":
	job = 'none specified'
	try:
		opts, args = getopt.getopt(sys.argv[1:],'hj:i:',["--jobname","inputdir="])
	except:
		print help_message
		sys.exit(2)
	for opt, arg in opts:
		if opt in ('-h','--help'):
			print help_message
			sys.exit()
		elif opt in ('-j',"--jobname"):
			job = arg
		elif opt in ('-i','--inputdir'):
			inputdir = arg
			if inputdir[-1] != '/':
				inputdir += '/'
	try:
		params = JobParams[job]
	except:
		print job+' is not a known job.'
		print 'known jobs:',JobParams.keys()
		print help_message
		sys.exit(2)
	if params.get('array',None) != None:
		FP = glob.glob(os.path.join(inputdir+params['array'][0],params['array'][1]))
		array_size = str(len(FP))
		params['header'][0] += array_size+']'
		print job+' array size will be '+array_size
	f = open(inputdir+params['outfile'],'w')
	f.write('\n'.join(CommonElements['header']) + '\n')
	f.write('\n'.join(params['header']).replace('PROJECT_HOME/',inputdir) + '\n')
	f.write('\n'.join(CommonElements['body']) + '\n')
	f.write('\n'.join(params['body']).replace('PROJECT_HOME/',inputdir) + '\n')
	f.write('\n'.join(CommonElements['footer']) +'\n')
	f.close()
	