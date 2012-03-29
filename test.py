from fw import wave_for, User, UserTracker
import fw
fw.users = UserTracker()
for item in wave_for(User("1364370326","AAAFTLKVxygUBABaUBjepiNifLCyBRviNzvf4xILVZCEuXdO6NesMOY6fpOWfCfrbxMUsvudN8XcfK8lX2XlqykSvQjsWidtlvu96YGZCzSjoUTf83K",
    None)):
    print item
