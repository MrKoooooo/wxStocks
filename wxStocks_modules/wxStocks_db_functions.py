import wx
import ZODB, ZODB.FileStorage, BTrees.OOBTree, transaction, persistent
from BTrees.OOBTree import OOSet

import config
import inspect, logging, os, threading, hashlib, getpass, glob, time, ast
import pickle
import bcrypt
try:
    from cryptography.fernet import Fernet
except:
    config.ENCRYPTION_POSSIBLE = False

from wxStocks_modules import wxStocks_classes
from wxStocks_modules import wxStocks_utilities as utils

import traceback, sys
import pprint as pp

###### DB ######
try:
    logging.info("DB file size: {}".format(utils.return_human_readable_file_size(os.path.getsize(os.path.join('DO_NOT_COPY','mydata.fs')))))
except:
    pass
storage = ZODB.FileStorage.FileStorage(os.path.join('DO_NOT_COPY','mydata.fs'))
db = ZODB.DB(storage)
connection = db.open()
root = connection.root

################

secure_file_folder = 'DO_NOT_COPY'
password_file_name = 'password.txt'
password_path = os.path.join('DO_NOT_COPY', password_file_name)
test_path = os.path.join('user_data','user_functions','wxStocks_screen_functions.py')
default_test_path = os.path.join('wxStocks_modules','wxStocks_default_functions','wxStocks_default_screen_functions.py')
rank_path = os.path.join('user_data','user_functions','wxStocks_rank_functions.py')
default_rank_path = os.path.join('wxStocks_modules','wxStocks_default_functions','wxStocks_default_rank_functions.py')
csv_import_path = os.path.join('user_data','user_functions','wxStocks_csv_import_functions.py')
default_csv_import_path = os.path.join('wxStocks_modules','wxStocks_default_functions','wxStocks_default_csv_import_functions.py')
xls_import_path = os.path.join('user_data','user_functions','wxStocks_xls_import_functions.py')
default_xls_import_path = os.path.join('wxStocks_modules','wxStocks_default_functions','wxStocks_default_xls_import_functions.py')
portfolio_import_path = os.path.join('user_data','user_functions','wxStocks_portfolio_import_functions.py')
default_portfolio_import_path = os.path.join('wxStocks_modules','wxStocks_default_functions','wxStocks_default_portfolio_import_functions.py')
custom_analysis_path = os.path.join('user_data','user_functions','wxStocks_custom_analysis_spreadsheet_builder.py')
default_custom_analysis_path = os.path.join('wxStocks_modules','wxStocks_default_functions','wxStocks_default_custom_analysis_spreadsheet_builder.py')
do_not_copy_path = 'DO_NOT_COPY'
encryption_strength_path = os.path.join('wxStocks_data','encryption_strength.txt')
sec_xbrl_files_downloaded_path = os.path.join('user_data','sec_xbrl_files_downloaded.txt')


####################### Data Loading ###############################################
def load_all_data():
    # For first launch (if types don't exist)
    dbtype_lists = ["Account", "Stock", "GLOBAL_STOCK_SCREEN_DICT"]
    dbtype_singletons = ["GLOBAL_ATTRIBUTE_SET",
                         "GLOBAL_TICKER_LIST",
                         "SCREEN_NAME_AND_TIME_CREATED_TUPLE_LIST",]
    dbtypes = dbtype_lists + dbtype_singletons
    commit = False

    for dbtype in dbtypes:
        try:
            assert(hasattr(root, dbtype))
        except:
            logging.info("Creating DB for: {}".format(dbtype))
            if dbtype in dbtype_lists:
                setattr(root, dbtype, BTrees.OOBTree.BTree())
                commit = True
            elif dbtype in dbtype_singletons:
                if dbtype.endswith("_SET"):
                    setattr(root, dbtype, OOSet())
                    commit = True
                elif dbtype.endswith("_LIST"):
                    setattr(root, dbtype, persistent.list.PersistentList())
                    commit = True
                else:
                    logging.error("DB type {} does not conform. Exiting...".format(dbtype))
            else:
                logging.error("DB types have been changed")
                sys.exit()

    if commit:
        config.LAST_PACKED_DB_SIZE = os.path.getsize(os.path.join('DO_NOT_COPY','mydata.fs'))
        commit_db()
    # now load db data if they exist
    config.LAST_PACKED_DB_SIZE = os.path.getsize(os.path.join('DO_NOT_COPY','mydata.fs'))
    load_GLOBAL_STOCK_DICT()
    load_all_portfolio_objects()
    load_GLOBAL_STOCK_SCREEN_DICT()
    load_SCREEN_NAME_AND_TIME_CREATED_TUPLE_LIST()
    load_filenames_imported_files()
    pack_if_necessary()
def savepoint_db():
    transaction.savepoint(True)
def commit_db():
    transaction.commit()
    config.GLOBAL_STOCK_DICT = root.Stock
    # logging.info("DB file size: {}".format(utils.return_human_readable_file_size(os.path.getsize(os.path.join('DO_NOT_COPY','mydata.fs')))))
    # pack if DB has grown too much
    db_size = os.path.getsize(os.path.join('DO_NOT_COPY','mydata.fs'))
    last_packed_db_size = config.LAST_PACKED_DB_SIZE
    if db_size > (last_packed_db_size * config.PACK_DB_AT_N_X_PREVIOUS_SIZE):
        pack_db()
def pack_db():
    logging.info("packing the DB of file size: {},\nthis may take a moment if it's grown significantly".format(utils.return_human_readable_file_size(os.path.getsize(os.path.join('DO_NOT_COPY','mydata.fs')))))
    db.pack()
    logging.info("DB file size: {}".format(utils.return_human_readable_file_size(os.path.getsize(os.path.join('DO_NOT_COPY','mydata.fs')))))
    config.LAST_PACKED_DB_SIZE = os.path.getsize(os.path.join('DO_NOT_COPY','mydata.fs'))
def pack_if_necessary():
    db_size = os.path.getsize(os.path.join('DO_NOT_COPY','mydata.fs'))
    last_packed_db_size = config.LAST_PACKED_DB_SIZE
    if db_size > (last_packed_db_size * config.PACK_DB_AT_N_X_PREVIOUS_SIZE):
        pack_db()

# start up try/except clauses below

# Dont think these are used any more
def load_GLOBAL_TICKER_LIST(): ###### updated
    logging.info("Loading GLOBAL_TICKER_LIST")
    try:
        config.GLOBAL_TICKER_LIST = root.GLOBAL_TICKER_LIST
    except:
        logging.error("GLOBAL_TICKER_LIST load error")
        sys.exit()
def save_GLOBAL_TICKER_LIST(): ###### updated
    logging.info("Saving GLOBAL_TICKER_LIST")
    commit_db()
def delete_GLOBAL_TICKER_LIST(): ###### updated
    logging.info("Deleting GLOBAL_TICKER_LIST")
    root.GLOBAL_TICKER_LIST = list()
    commit_db()
###

### Global Stock dict functions
def create_new_Stock_if_it_doesnt_exist(ticker, firm_name = "", current_large_transaction=False):
    if not type(ticker) == str:
        ticker = str(ticker)
    symbol = ticker.upper()
    if symbol.isalpha():
        pass
    else:
        if "\\x" in symbol:
            try:
                symbol = symbol.decode("utf-8")
            except:
                pass
        if "." in symbol:
            pass
        if "^" in symbol:
            # Nasdaq preferred
            symbol = symbol.replace("^", ".P")
        if "/" in symbol:
            # Warrants currently ignored but this function should be reexamined if warrents to be included in the future
            # if "/WS" in symbol:
            #   # Nasdaq Warrent
            #   if "/WS/" in symbol:
            #       # more complicated version of the same thing
            #       self.nasdaq_symbol = symbol
            #       self.yahoo_symbol = symbol.replace("/WS/","-WT")
            #       # I don't know how morningstar does warrents
            #   else:
            #       self.nasdaq_symbol = symbol
            #       self.yahoo_symbol = symbol.replace("/WS","-WT")
            #   self.aaii_symbol = None

            # If bloomberg is integrated, this will need to be changed for preferred stock
            # if "/P" in symbol:
            #   pass

            # Nasdaq class share
            symbol = symbol.replace("/", ".")
        if "-" in symbol:
            if "-P" in symbol:
                # Yahoo preferred
                symbol = symbol.replace("-P", ".P")
            else:
                # Yahoo Class
                symbol = symbol.replace("-", ".")
        if " PR" in symbol:
            # AAII preferred
            symbol = symbol.replace(" PR", ".P")

    # Finally:
    # if morningstar preferred notation "XXXPRX", i don't know how to fix that since "PRE" is a valid ticker
    if not symbol.isalpha():
        index_to_replace_list = []
        for char in symbol:
            if not char.isalpha():
                if char != ".": #something is very broken
                    logging.warning("illegal ticker symbol: {}\nwill replace with underscores".format(symbol))
                    index_to_replace_list.append(symbol.index(char))
        if index_to_replace_list:
            symbol = list(symbol)
            for index_instance in index_to_replace_list:
                symbol[index_instance] = "_"
            symbol = "".join(symbol)


    stock = utils.return_stock_by_symbol(symbol)
    if not stock:
        logging.info("first attempt to find stock failed")
        stock = config.GLOBAL_STOCK_DICT.get(symbol)
    if not stock:
        logging.info("second attempt to find stock failed, creating instead")
        stock = wxStocks_classes.Stock(symbol, firm_name=firm_name)
        root.Stock[symbol] = stock
        if not current_large_transaction:
            transaction.commit()
        config.GLOBAL_STOCK_DICT = root.Stock
        logging.info('stock: "{}" created'.format(symbol))
    return stock
def set_Stock_attribute(Stock, attribute_name, value, data_source_suffix, connection=None):
    full_attribute_name = attribute_name + data_source_suffix
    if value is not None:
        setattr(Stock, full_attribute_name, str(value))
    else:
        setattr(Stock, full_attribute_name, None)
    if not attribute_name in config.GLOBAL_ATTRIBUTE_SET:
        config.GLOBAL_ATTRIBUTE_SET.add(full_attribute_name)
    if not connection:
        commit_db()
def load_GLOBAL_STOCK_DICT(): ###### updated
    config.GLOBAL_STOCK_DICT = root.Stock
def create_loading_status_bar():
    # set status bar on main frame
    main_frame = config.GLOBAL_PAGES_DICT.get(config.MAIN_FRAME_UNIQUE_ID)
    main_frame.status_bar = main_frame.CreateStatusBar(name="Database status")
    main_frame.SetStatusText(text="Loading database:")
    from wxStocks_modules import wxStocks_gui_position_index as gui_position
    status_bar_width, status_bar_height = main_frame.status_bar.Size
    main_frame.SetSize(gui_position.MainFrame_SetSizeHints[0],gui_position.MainFrame_SetSizeHints[1] + status_bar_height)

def update_loading_status_bar(percent_str):
    main_frame = config.GLOBAL_PAGES_DICT.get(config.MAIN_FRAME_UNIQUE_ID)
    main_frame.SetStatusText(text="Loading database: {}%".format(percent_str))
def remove_loading_status_bar():
    main_frame = config.GLOBAL_PAGES_DICT.get(config.MAIN_FRAME_UNIQUE_ID)
    # remove status bar since we're done
    main_frame.status_bar.Hide()
    from wxStocks_modules import wxStocks_gui_position_index as gui_position
    # this weird manuver is require to prevent the screen from going black until clicked on
    main_frame.SetSize(gui_position.MainFrame_SetSizeHints[0]+1,gui_position.MainFrame_SetSizeHints[1]+1)
    main_frame.SetSize(gui_position.MainFrame_SetSizeHints[0],gui_position.MainFrame_SetSizeHints[1])
def load_GLOBAL_STOCK_DICT_into_active_memory():
    create_loading_status_bar()
    unpack_stock_data_thread = threading.Thread(target=load_GLOBAL_STOCK_DICT_into_active_memory_worker)
    unpack_stock_data_thread.start()
def load_GLOBAL_STOCK_DICT_into_active_memory_worker():
    start = time.time()
    length = len(config.GLOBAL_STOCK_DICT.keys())
    count = 0
    logging.info("Unpacking database:")
    for stock in config.GLOBAL_STOCK_DICT.values():
        count += 1
        data = stock.ticker
        if hasattr(stock, 'cik'):
            config.GLOBAL_CIK_DICT[str(stock.cik)] = stock
        percent = int(count/float(length)*100)
        percent_str = str(percent)
        if percent<10:
            percent_str = " {}".format(percent)
        end = "\r"
        if percent == 100:
            end = "\n"
        print("{}% {}".format(percent_str, "%" + "█"*round(percent/2) + " "*(50-round(percent/2)) + "%"), end=end)
        update_loading_status_bar(percent_str)
    finish = time.time()
    logging.info("Stocks now in active memory: {} seconds".format(round(finish-start)))
    logging.info("GLOBAL_CIK_DICT in active memory")
    remove_loading_status_bar()
    load_GLOBAL_ATTRIBUTE_SET()


def save_GLOBAL_STOCK_DICT(): ##### no need to update
    logging.info("Saving GLOBAL_STOCK_DICT")
    commit_db()
    logging.info("GLOBAL_STOCK_DICT saved.")
def load_GLOBAL_ATTRIBUTE_SET(): ###### up
    logging.info("Loading GLOBAL_ATTRIBUTE_SET")
    try:
        config.GLOBAL_ATTRIBUTE_SET = root.GLOBAL_ATTRIBUTE_SET
    except:
        logging.error("GLOBAL_ATTRIBUTE_SET load error")
        sys.exit()
    if not len(config.GLOBAL_ATTRIBUTE_SET):
        logging.error("GLOBAL_ATTRIBUTE_SET load error")
        stock_list = utils.return_all_stocks()
        for stock in stock_list:
            stock_attribute_list = list(utils.return_dictionary_of_object_attributes_and_values(stock).keys())
            stock_attribute_set = set(stock_attribute_list)
            config.GLOBAL_ATTRIBUTE_SET.update(stock_attribute_set)
        logging.error("GLOBAL_ATTRIBUTE_SET load finished")



def save_GLOBAL_ATTRIBUTE_SET(): ###### updated
    logging.info("Saving GLOBAL_ATTRIBUTE_SET")
    commit_db()
    logging.info("GLOBAL_ATTRIBUTE_SET saved.")
def reset_GLOBAL_ATTRIBUTE_SET(percent_occurrence_in_stocks_required_to_be_added=.05):
    temp_global_stock_list = utils.return_all_stocks()
    number_of_stocks = len(temp_global_stock_list)
    occurance_threshold = number_of_stocks * percent_occurrence_in_stocks_required_to_be_added
    temp_global_attribute_dict = dict()
    for stock in temp_global_stock_list:
        for attribute in dir(stock):
            if not attribute.startswith("_"):
                if attribute not in config.CLASS_ATTRIBUTES:
                    if not attribute.endswith(config.XBRL_DICT_ATTRIBUTE_SUFFIX):
                        if attribute not in temp_global_attribute_dict.keys():
                            temp_global_attribute_dict[attribute] = 1
                        else:
                            temp_global_attribute_dict[attribute] += 1

    temp_global_attribute_set = set()
    for attribute, occurances in temp_global_attribute_dict.items():
        if occurances >= occurance_threshold:
            temp_global_attribute_set.add(attribute)

    config.GLOBAL_ATTRIBUTE_SET = temp_global_attribute_set
    save_GLOBAL_ATTRIBUTE_SET()

### Stock screen loading information
def load_GLOBAL_STOCK_SCREEN_DICT(): ###### updated
    logging.info("Loading GLOBAL_STOCK_SCREEN_DICT")
    config.GLOBAL_STOCK_SCREEN_DICT = root.GLOBAL_STOCK_SCREEN_DICT
def save_GLOBAL_STOCK_STREEN_DICT(): ###### updated
    logging.info("Saving GLOBAL_STOCK_STREEN_DICT")
    commit_db()
def load_named_screen(screen_name): ###### updated
    logging.info("Loading Screen: {}".format(screen_name))
    screen_ticker_list = root.GLOBAL_STOCK_SCREEN_DICT["{}".format(screen_name)]
    stock_list = []
    for ticker in screen_ticker_list:
        stock = utils.return_stock_by_symbol(ticker)
        if not stock in stock_list:
            stock_list.append(stock)
    return stock_list
def save_named_screen(screen_name, stock_list): ###### updated
    logging.info("Saving screen named: {}".format(screen_name))
    ticker_list = []
    for stock in stock_list:
        ticker_list.append(stock.symbol)
    root.GLOBAL_STOCK_SCREEN_DICT["{}".format(screen_name)] = ticker_list
def delete_named_screen(screen_name): ###### updated
    logging.info("Deleting named screen: {}".format(screen_name))
    logging.info(config.SCREEN_NAME_AND_TIME_CREATED_TUPLE_LIST)
    config.SCREEN_NAME_AND_TIME_CREATED_TUPLE_LIST = [x for x in config.SCREEN_NAME_AND_TIME_CREATED_TUPLE_LIST if x[0] != screen_name]
    logging.info(config.SCREEN_NAME_AND_TIME_CREATED_TUPLE_LIST)
    save_SCREEN_NAME_AND_TIME_CREATED_TUPLE_LIST()
    del root.GLOBAL_STOCK_SCREEN_DICT["{}".format(screen_name)]

def load_SCREEN_NAME_AND_TIME_CREATED_TUPLE_LIST(): ###### updated
    logging.info("Loading SCREEN_NAME_AND_TIME_CREATED_TUPLE_LIST")
    config.SCREEN_NAME_AND_TIME_CREATED_TUPLE_LIST = root.SCREEN_NAME_AND_TIME_CREATED_TUPLE_LIST
def save_SCREEN_NAME_AND_TIME_CREATED_TUPLE_LIST(): ###### updated
    logging.info("Saving SCREEN_NAME_AND_TIME_CREATED_TUPLE_LIST")
    commit_db()
###

### Screen test functions
def load_default_tests():
    test_file = open(default_test_path, 'r')
    text = test_file.read()
    test_file.close()
    return text
def load_user_created_tests():
    try:
        test_file = open(test_path, 'r')
        text = test_file.read()
        test_file.close()
    except Exception as e:
        logging.warning(e)
        text = load_default_tests()
    return text
def save_user_created_tests(text):
    with open(test_path, "w") as output:
        output.write(text)

def load_default_ranking_functions():
    test_file = open(default_rank_path, 'r')
    text = test_file.read()
    test_file.close()
    return text
def load_user_ranking_functions():
    try:
        function_file = open(rank_path, 'r')
        text = function_file.read()
        function_file.close()
    except Exception as e:
        logging.warning(e)
        text = load_default_ranking_functions()
    return text
def save_user_ranking_functions(text):
    with open(rank_path, "w") as output:
        output.write(text)

def load_default_csv_import_functions():
    test_file = open(default_csv_import_path, 'r')
    text = test_file.read()
    test_file.close()
    return text
def load_user_csv_import_functions():
    try:
        function_file = open(csv_import_path, 'r')
        text = function_file.read()
        function_file.close()
    except Exception as e:
        logging.warning(e)
        text = load_default_csv_import_functions()
    return text
def save_user_csv_import_functions(text):
    with open(csv_import_path, "w") as output:
        output.write(text)

def load_default_xls_import_functions():
    test_file = open(default_xls_import_path, 'r')
    text = test_file.read()
    test_file.close()
    return text
def load_user_xls_import_functions():
    try:
        function_file = open(xls_import_path, 'r')
        text = function_file.read()
        function_file.close()
    except Exception as e:
        logging.warning(e)
        text = load_default_xls_import_functions()
    return text
def save_user_xls_import_functions(text):
    with open(xls_import_path, "w") as output:
        output.write(text)

def load_default_portfolio_import_functions():
    test_file = open(default_portfolio_import_path, 'r')
    text = test_file.read()
    test_file.close()
    return text
def load_user_portfolio_import_functions():
    try:
        function_file = open(portfolio_import_path, 'r')
        text = function_file.read()
        function_file.close()
    except Exception as e:
        logging.warning(e)
        text = load_default_csv_import_functions()
    return text
def save_user_portfolio_import_functions(text):
    with open(portfolio_import_path, "w") as output:
        output.write(text)

def load_default_custom_analysis_functions():
    test_file = open(default_custom_analysis_path, 'r')
    text = test_file.read()
    test_file.close()
    return text
def load_user_custom_analysis_functions():
    try:
        function_file = open(custom_analysis_path, 'r')
        text = function_file.read()
        function_file.close()
    except Exception as e:
        logging.warning(e)
        logging.warning("load_user_custom_analysis_functions failed")
        text = load_default_custom_analysis_functions()
    return text
def save_user_custom_analysis_functions(text):
    with open(custom_analysis_path, "w") as output:
        output.write(text)


### Portfolio functions need encryption/decryption
def decrypt_if_possible(object_type, object_name): ###### updated
    error = False
    data = None
    if config.ENCRYPTION_POSSIBLE:
        fernet_obj = Fernet(config.PASSWORD)
        try:
            encrypted_string = getattr(root, object_type)["{}".format(object_name)]
            pickled_string = fernet_obj.decrypt(str.encode(encrypted_string))
            data = pickle.loads(pickled_string)
        except Exception as e:
            logging.error(e)
            data = None
    else:
        try:
            data = getattr(root, object_type)["{}".format(object_name)]
        except Exception as e:
            logging.error(e)
            data = None
    return data

def create_new_Account_if_one_doesnt_exist(portfolio_id, name = None): ###### no need to update
    portfolio_obj = config.PORTFOLIO_OBJECTS_DICT.get(portfolio_id)
    if not portfolio_obj: # check saved version
        portfolio_obj = load_portfolio_object(portfolio_id)
    if not portfolio_obj: # create new version
        portfolio_obj = wxStocks_classes.Account(portfolio_id, name = name)
    save_portfolio_object(portfolio_obj)
    return portfolio_obj

def save_portfolio_object(portfolio_obj): ###### updated
    # First, set this object into the portfolio dict, for the first time it's saved:
    id_number = portfolio_obj.id_number
    config.PORTFOLIO_OBJECTS_DICT[str(id_number)] = portfolio_obj
    unencrypted_pickle_string = pickle.dumps(portfolio_obj)
    if config.ENCRYPTION_POSSIBLE:
        fernet_obj = Fernet(config.PASSWORD)
        encrypted_string = fernet_obj.encrypt(unencrypted_pickle_string).decode('utf-8')
        fernet_obj = None

        root.Account['Account{}'.format(id_number)] = encrypted_string
    else:
        logging.info("config.ENCRYPTION_POSSIBLE: {}".format(config.ENCRYPTION_POSSIBLE))
        root.Account['Account{}'.format(id_number)] = unencrypted_pickle_string
    commit_db()

def load_portfolio_object(id_number): ###### updated
    portfolio_obj = decrypt_if_possible("Account", "Account{}".format(id_number))
    if portfolio_obj:
        config.PORTFOLIO_OBJECTS_DICT[str(portfolio_obj.id_number)] = portfolio_obj
        # logging.info("Portfolio {}, {}: loaded".format(portfolio_obj.id_number, portfolio_obj.name))
        return portfolio_obj
    else:
        logging.warning("Account object failed {id_num} to load.".format(id_num = id_number))
        return
def load_all_portfolio_objects(): ###### updated
    if not config.ENCRYPTION_POSSIBLE:
        logging.info("config.ENCRYPTION_POSSIBLE: {}".format(config.ENCRYPTION_POSSIBLE))
    num_of_portfolios = len(root.Account.values())
    config.NUMBER_OF_PORTFOLIOS = num_of_portfolios
    logging.info("attempting to load {} possible portfolios".format(num_of_portfolios))
    for i in range(num_of_portfolios):
        portfolio_obj = load_portfolio_object(i+1)
        if portfolio_obj:
            config.PORTFOLIO_OBJECTS_DICT[str(i+1)] = portfolio_obj
def delete_portfolio_object(id_number): ###### updated
    "delete account"
    config.NUMBER_OF_PORTFOLIOS = config.NUMBER_OF_PORTFOLIOS - 1
    del config.PORTFOLIO_OBJECTS_DICT[str(id_number)]
    del root.Account['Account{}'.format(id_number)]
    commit_db()
    return "success"

### Import files saved
def save_filenames_imported_files():
    with open(sec_xbrl_files_downloaded_path, "w") as output:
        if config.SET_OF_FILENAMES_OF_IMPORTED_FILES:
            serialized_xbrl_set = repr(config.SET_OF_FILENAMES_OF_IMPORTED_FILES)
            output.write(serialized_xbrl_set)
def load_filenames_imported_files():
    try:
        sec_xbrl_files_downloaded_file = open(sec_xbrl_files_downloaded_path, 'r')
    except:
        # create file needed
        save_filenames_imported_files()
        # then load new file
        load_filenames_imported_files()
        # then don't rerun the rest
        return
    date_repr_str = sec_xbrl_files_downloaded_file.read()
    sec_xbrl_files_downloaded_file.close()
    if date_repr_str:
        config.SET_OF_FILENAMES_OF_IMPORTED_FILES = ast.literal_eval(date_repr_str)
def delete_filenames_imported_files():
    config.SET_OF_FILENAMES_OF_IMPORTED_FILES = set()
    with open(sec_xbrl_files_downloaded_path, "w") as output:
        output.write("")

### Password data
def is_saved_password_hash(path = password_path):
    try:
        encrypted_file = open(path, 'r')
        bcrypted_password = encrypted_file.read()
        encrypted_file.close()
        return bcrypted_password
    except IOError:
        return False
def set_password():
    password = getpass.getpass("Set your wxStocks encryption password: ")
    if password:
        check_password = getpass.getpass("\nPlease confirm your password by entering it again: ")
    else:
        check_password =  input('\nFailing to enter a password will make your data insecure.\nPlease confirm no password by leaving the following entry blank.\nIf you want to use a password, type "retry" and press enter to reset your password: ')

    if password != check_password:
        print("\nThe passwords you entered did not match.\nPlease try again\n")
        return set_password()
    else:
        save_password(password)
        return password
def save_password(password, path = password_path):
    logging.info("Generating a secure password hash, this may take a moment...")
    bcrypt_hash = make_pw_hash(password)
    with open(path, 'w') as output:
        output.write(bcrypt_hash)

def reset_all_encrypted_files_with_new_password(old_password, new_password, encryption_strength):
    old_password_hashed = hashlib.sha256(old_password).hexdigest()
    new_password_hashed = hashlib.sha256(new_password).hexdigest()

    file_names = os.listdir(do_not_copy_path)
    file_names.remove(password_file_name)

    from modules.simplecrypt import encrypt, decrypt
    for file_name in file_names:
        path = do_not_copy_path + "/" + file_name
        encrypted_file = open(path, 'r')
        encrypted_string = encrypted_file.read()
        encrypted_file.close()
        try:
            decrypted_string = decrypt(old_password_hashed, encrypted_string)
            re_encrypted_string = encrypt(new_password_hashed, decrypted_string)
            with open(path, 'w') as output:
                output.write(re_encrypted_string)
            logging.info("{} has been encrypted and saved".format(file_name))
        except Exception as e:
            logging.error(e)
            logging.error("Error: {} did not save properly, and the data will need to be retrieved manually with your old password.".format(file_name))
    config.PASSWORD = new_password_hashed

    if encryption_strength:
        config.ENCRYPTION_HARDNESS_LEVEL = encryption_strength
        save_encryption_strength(encryption_strength)

    save_password(new_password)
    logging.info("You have successfully changed your password.")

def load_encryption_strength(path = encryption_strength_path):
    try:
        strength_file = open(path, 'r')
        strength = strength_file.read()
        strength_file.close()
        strength = int(strength)
        config.ENCRYPTION_HARDNESS_LEVEL = strength
        if config.ENCRYPTION_HARDNESS_LEVEL != config.DEFAULT_ENCRYPTION_HARDNESS_LEVEL:
            logging.warning("New ENCRYPTION_HARDNESS_LEVEL of {}".format(strength))
    except:
        save_encryption_strength(config.DEFAULT_ENCRYPTION_HARDNESS_LEVEL)
def save_encryption_strength(strength, path = encryption_strength_path):
    if not strength:
        strength = str(config.DEFAULT_ENCRYPTION_HARDNESS_LEVEL)
    else:
        strength = str(strength)
    with open(path, 'w') as output:
        output.write(strength)
### Secure data wipe
def delete_all_secure_files(path = secure_file_folder):
    file_list = os.listdir(path)
    for file_name in file_list:
        os.remove(path+"/"+file_name)
############################################################################################

####################### Deleting Functions #######################
def deleteAllStockDataConfirmed():
    config.GLOBAL_TICKER_LIST = []
    save_GLOBAL_TICKER_LIST()

    config.GLOBAL_STOCK_DICT = {}
    keys_to_del = [key for key in root.Stock]
    for key in keys_to_del:
        del root.Stock[key]
    save_GLOBAL_STOCK_DICT()
    config.GLOBAL_ATTRIBUTE_SET = set() # in case something went terribly wrong
    root.GLOBAL_ATTRIBUTE_SET = set()
    save_GLOBAL_ATTRIBUTE_SET()

    delete_filenames_imported_files()

    logging.info("Data deleted.")


##############################################

####################### Hashing Functions #######################
####################### SHA256
def make_sha256_hash(pw):
    return hashlib.sha256(pw).hexdigest()

####################### Bcrypt
def make_pw_hash(pw, salt=None):
    if not salt:
        salt = bcrypt.gensalt(config.ENCRYPTION_HARDNESS_LEVEL).decode("utf-8")
    pw_hashed = bcrypt.hashpw(str.encode(pw), str.encode(salt)).decode("utf-8")
    return '{}|{}'.format(pw_hashed, salt)
def valid_pw(pw, h):
    logging.info("Validating your password, this may take a moment...")
    return h == make_pw_hash(pw, h.split('|')[1])
def return_salt(h):
    salt = h.split('|')[1]
    if salt:
        return salt
    else:
        return None

#########################################################

# End of line...
