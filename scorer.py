def judge(question, expects, answer, results) -> bool:
    '''
    question: 'give', expects: 'give'
    the expect is in the answer
    '''
    return expects.lower().strip() in answer.lower()
