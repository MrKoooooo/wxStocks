import os, glob
from wxStocks_modules.wxStocks_classes import CustomAnalysisSpreadsheetCell as Cell

def line_number():
    import inspect
    """Returns the current line number in our program."""
    #print 'remove this temporary line number function'
    return "File: %s\nLine %d:" % (inspect.getframeinfo(inspect.currentframe()).filename.split("/")[-1], inspect.currentframe().f_back.f_lineno)


'''
Here, you must use the class "Cell" to refer to a cell you want processed.
This allows the program to process your data in to function wxPython code.
The class Cell has the following default keyword arguments:

my_cell = Cell(
            row = None,
            col = None,
            text = None,
            background_color = None,
            text_color = None,
            font_size = None,
            bold = False,
            function = None
            )

Import your own custom functions from the "functions_for_custom_analysis_go_in_here" folder.
Your import statements should look like this:

def my_custom_spreadsheet():
    from functions_for_custom_analysis_go_in_here import your_file
    data = your_file.your_function()
'''

def rms_stock_analysis(stock_list):
    "an RMS analysis"
    from functions_for_custom_analysis_go_in_here import aaii_formulas as aaii
    import numpy
    import pprint as pp
    from collections import namedtuple

    default_row_buffer_before_stocks = 2
    all_cells_list = []
    row_list = []

    class Attribute(object):
        def __init__(self, name, function, weight, maximum, minimum, size_factor, col):
            self.name = name
            self.function = function
            self.weight = weight
            self.maximum = maximum
            self.minimum = minimum
            self.size_factor = size_factor
            self.col = col
            self.avg = None
            self.std = None

    class Row(object):
        "used to look at a whole row of stock' data at the same time"
        def __init__(self, stock):
            self.stock = stock

    def return_Row_obj_else_create(stock):
        correct_row = None
        for row in row_list:
            if row.stock is stock:
                correct_row = row
        if not correct_row:
            correct_row = Row(stock)
            row_list.append(correct_row)
        return correct_row


    def top_row():
        text = 'BUY CANDIDATES'
        top_row_cell = Cell(row = 0, col=0, text=text)
        all_cells_list.append(top_row_cell)
    def gen_attribute_list(row = 1):
        #print line_number(), column_text_list
        cell_list_to_return = []
        for attribute_obj in attribute_list:
            attribute_cell = Cell(row = row, col = attribute_obj.col, text = attribute_obj.name, col_title = attribute_obj.name)
            all_cells_list.append(attribute_cell)
    def create_rows_of_stock_data(stock_list = stock_list):
        rows_before_stock_data = 2
        rows_list = []
        for stock in stock_list:
            stock_row = return_Row_obj_else_create(stock)
            for attribute_obj in attribute_list:
                try:
                    data = attribute_obj.function(stock)
                except: # in case it throws an attribute error
                    data = None
                data_cell = Cell(text = data) # this will be thrown out later
                setattr(stock_row, attribute_obj.name, data_cell)

    def create_data_scores(row_list):
        for attribute_obj in attribute_list:
            # first iterate over each attribute, to find the mean and standard dev

            attribute_data_list = []
            for row in row_list:
                data_cell = getattr(row, attribute_obj.name)
                data = data_cell.text
                if data is not None:
                    if attribute_obj.minimum or attribute_obj.maximum:
                        # normalize data
                        if data < attribute_obj.minimum:
                            data = attribute_obj.minimum
                            data_cell.text = data
                            data_cell.text_color = "#333333"
                        elif data > attribute_obj.maximum:
                            data = attribute_obj.maximum
                            data_cell.text = data
                            data_cell.text_color = "#333333"
                attribute_data_list.append(data)

            not_none_data_list = []
            for x in attribute_data_list:
                try:
                    float(x)
                    not_none_data_list.append(x)
                except:
                    # not a number
                    pass

            if not not_none_data_list:
                # no reason to look at data, all is None
                continue


            try: # get average and standard deviation if possible
                data_avg = numpy.average(not_none_data_list, axis=0)

                data_list_averaged_data = []
                for data in attribute_data_list:
                    if data is not None:
                        data_list_averaged_data.append(data)
                    else:
                        data_list_averaged_data.append(data_avg)
                data_std = numpy.std(data_list_averaged_data)

                # set attribute average standard deviation for colors later
                attribute_obj.avg = data_avg
                attribute_obj.std = data_std

                for stock_row in row_list:
                    b =  attribute_obj.function(stock_row.stock)
                    mu = float(data_avg)
                    sigma = float(data_std)
                    if b is not None and mu is not None and sigma:
                        z_score = (b-mu)/sigma
                    else:
                        z_score = None
                    z_score_cell = Cell(text = z_score)
                    setattr(stock_row, str(attribute_obj.name) + "__z_score", z_score_cell)
            except Exception, e:
                print line_number(), e

        for stock_row in row_list:
            score = 0.0
            for attribute_obj in attribute_list:
                weight = attribute_obj.weight
                if weight is not None:
                    try:
                        z_score_data_cell = getattr(stock_row, attribute_obj.name + "__z_score")
                        z_score_data = z_score_data_cell.text
                        if z_score_data is not None:
                            modified_score_value = z_score_data * weight
                            if attribute_obj.size_factor:
                                if attribute_obj.size_factor == "big":
                                    score += modified_score_value
                                elif attribute_obj.size_factor == "small":
                                    score -= modified_score_value
                                else:
                                    print line_number(), "Error: something went wrong here"
                                z_score_data_cell.text = score
                    except Exception, e:
                        print line_number(), e
            stock_row.Score.text = score

    def find_score_standard_deviations(row_list):
        score_list = []
        for stock_row in row_list:
            score = stock_row.Score.text
            if score is not None:
                if score > 1000:
                    score = 1000
                if score < -1000:
                    score = -1000
                score_list.append(score)
        score_avg = numpy.average(score_list, axis=0)
        score_std = numpy.std(score_list)

        for attribute_obj in attribute_list:
            if attribute_obj.name == "Score":
                attribute_obj.avg = score_avg
                attribute_obj.std = score_std

    def sort_row_list_and_convert_into_cells(row_list):
        ''' this is a complex function,
            it sorts by row,
            then find each attribute,
            then looks for the attribute object,
            then sees if the value is outside the bounds of a standard deviation,
            then sets object colors
        '''
        extra_rows = 0
        extra_rows += default_row_buffer_before_stocks

        score_avg = None
        score_std = None
        # first, get score avg and std
        for attribute_obj in attribute_list:
            if attribute_obj.name == "Score":
                score_avg = attribute_obj.avg
                score_std = attribute_obj.std

        first_iteration = True
        last_sigma_stage = None

        row_list.sort(key = lambda x: x.Score.text, reverse=True)
        for stock_row in row_list:
            # Now, check if we need a blank row between sigma's
            if   stock_row.Score.text > (score_avg + (score_std * 3)):
                # greater than 3 sigmas
                if first_iteration:
                    first_iteration = False
                    last_sigma_stage = 3
            elif stock_row.Score.text > (score_avg + (score_std * 2)):
                # greater than 2 sigmas
                if first_iteration:
                    first_iteration = False
                    last_sigma_stage = 2
                if last_sigma_stage > 2:
                    last_sigma_stage = 2

                    empty_row_num = row_list.index(stock_row) + extra_rows
                    empty_cell = Cell(text = " ", col = 0, row = empty_row_num, row_title = "2 sigma")
                    all_cells_list.append(empty_cell)
                    extra_rows += 1

            elif stock_row.Score.text > (score_avg + (score_std * 1)):
                # greater than 1 sigma
                if first_iteration:
                    first_iteration = False
                    last_sigma_stage = 1
                if last_sigma_stage > 1:
                    last_sigma_stage = 1

                    empty_row_num = row_list.index(stock_row) + extra_rows
                    empty_cell = Cell(text = " ", col = 0, row = empty_row_num, row_title = "1 sigma")
                    all_cells_list.append(empty_cell)
                    extra_rows += 1

            elif stock_row.Score.text > (score_avg + (score_std * 0)):
                # greater than avg
                if first_iteration:
                    first_iteration = False
                    last_sigma_stage = 0
                if last_sigma_stage > 0:
                    last_sigma_stage = 0

                    empty_row_num = row_list.index(stock_row) + extra_rows
                    empty_cell = Cell(text = " ", col = 0, row = empty_row_num, row_title = " ")
                    all_cells_list.append(empty_cell)
                    extra_rows += 1

                    empty_row_num = row_list.index(stock_row) + extra_rows
                    empty_cell = Cell(text = " ", col = 0, row = empty_row_num, row_title = "avg")
                    all_cells_list.append(empty_cell)
                    extra_rows += 1

                    empty_row_num = row_list.index(stock_row) + extra_rows
                    empty_cell = Cell(text = " ", col = 0, row = empty_row_num, row_title = " ")
                    all_cells_list.append(empty_cell)
                    extra_rows += 1

            elif stock_row.Score.text < (score_avg - (score_std * 1)):
                # greater than 1 sigma
                if first_iteration:
                    first_iteration = False
                    last_sigma_stage = -1
                if last_sigma_stage > -1:
                    last_sigma_stage = -1

                    empty_row_num = row_list.index(stock_row) + extra_rows
                    empty_cell = Cell(text = " ", col = 0, row = empty_row_num, row_title = "-1 sigma")
                    all_cells_list.append(empty_cell)
                    extra_rows += 1

            elif stock_row.Score.text < (score_avg - (score_std * 2)):
                # greater than 2 sigma
                if first_iteration:
                    first_iteration = False
                    last_sigma_stage = -2

                    empty_row_num = row_list.index(stock_row) + extra_rows
                    empty_cell = Cell(text = " ", col = 0, row = empty_row_num, row_title = "-2 sigma")
                    all_cells_list.append(empty_cell)
                    extra_rows += 1



            row_num = row_list.index(stock_row) + extra_rows


            for attribute_obj in attribute_list:
                data_cell = getattr(stock_row, attribute_obj.name)
                if data_cell.text is not None:
                    data = data_cell.text
                    background_color = None
                    if attribute_obj.avg is not None and attribute_obj.std is not None and data is not None:
                        if data > (attribute_obj.avg + attribute_obj.std):
                            # better than 1 standard deviation -> green!
                            background_color = "#CCFFCC"
                        elif data < (attribute_obj.avg - (attribute_obj.std * 2)):
                            # worse than 2 standard deviations -> red :/
                            background_color = "#F78181"
                        elif data < (attribute_obj.avg - attribute_obj.std):
                            # worse than 1 standard deviation -> orange
                            background_color = "#FFB499"
                    new_data_cell = Cell(text = data)
                    new_data_cell.row = row_num
                    new_data_cell.col = attribute_obj.col
                    new_data_cell.background_color = background_color
                    new_data_cell.text = data
                    try:
                        new_data_cell.row_title = stock_row.stock.ticker
                    except:
                        pass
                    all_cells_list.append(new_data_cell)

    def return_ticker(stock):
        return stock.ticker
    def return_name(stock):
        return stock.firm_name
    def return_volume(stock):
        return stock#.volume


    # attr  = Attribute("name",            function,                               weight, max,    min,    size,   col)
    score   = Attribute("Score",           None,                                   None,   None,   None,   None,   0)
    action  = Attribute("Action",          None,                                   None,   None,   None,   None,   1)
    ticker  = Attribute("Ticker",          return_ticker,                          None,   None,   None,   None,   2)
    price   = Attribute("Price",           None,                                   None,   None,   None,   None,   3)
    volume  = Attribute("AvgDly $K Vol",   None,                                   None,   None,   None,   None,   4)
    neff5h  = Attribute("Neff 5Yr H",      aaii.neff_ratio_5y,                     1.0,    10.,    0.,     "big",  5)
    neffttm = Attribute("Neff TTM H",      aaii.neff_TTM_historical,               1.0,    10.,    0.,     "big",  6)
    neff5f  = Attribute("Neff 5 Yr F",     aaii.neff_5_Year_future_estimate,       2.0,    10.,    0.,     "big",  7)
    margin  = Attribute("Mrgin %%Rnk",     aaii.marginPercentRank,                 1.0,    None,   None,   "big",  8)
    roe_rank= Attribute("ROE %%Rnk",       aaii.roePercentRank,                    2.0,    None,   None,   "big",  9)
    roe_dev = Attribute("ROE %%Dev",       aaii.roePercentDev,                     0.1,    2.,     None,   "small",10)
    ticker2 = Attribute("Ticker",          return_ticker,                          None,   None,   None,   None,   11)
    p2b_g   = Attribute("Prc2Bk Grwth",    aaii.price_to_book_growth,              0.1,    10.,    None,   "big",  12)
    p2r     = Attribute("Prc 2Rng",        aaii.price_to_range,                    0.1,    3.,     0.,     "big",  13)
    insiders= Attribute("Insdr %",         aaii.percentage_held_by_insiders,       0.1,    None,   None,   "big",  14)
    inst    = Attribute("NetInst Buy%",    aaii.percentage_held_by_institutions,   0.1,    None,   None,   "big",  15)
    current = Attribute("Cur Ratio",       aaii.current_ratio,                     0.1,    None,   None,   "big",  16)
    ltd2e   = Attribute("LTDbt / Eqty %",  aaii.longTermDebtToEquity,              0.1,    200.,   None,   "small",17)
    neffebit= Attribute("NeffEv Ebit",     aaii.neffEvEBIT,                        0.1,    10.,    0.,     "big",  18)
    neff3h  = Attribute("NeffCf 3yr H",    aaii.neffCf3Year,                       1.0,    10.,    0.,     "big",  19)
    name    = Attribute("Name",            return_name,                            None,   None,   None,   None,   20)
    score2  = Attribute("Score",           None,                                   None,   None,   None,   None,   21)

    attribute_list = [score, action, ticker, price, volume, neff5h, neffttm,
        neff5f, margin, roe_rank, roe_dev, ticker2, p2b_g, p2r, insiders, inst,
        current, ltd2e, neffebit, neff3h, name, score2]




    top_row()
    gen_attribute_list()
    create_rows_of_stock_data()
    create_data_scores(row_list)
    find_score_standard_deviations(row_list)
    sort_row_list_and_convert_into_cells(row_list)
    print "Done sorting spreadsheet"
    return all_cells_list






























