# -*- coding: utf-8 -*-
"""Time-Series. POLY

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1OA5HCpPOIaZeunP-5UiTt6qUhniMUp5B
"""

from google.colab import drive
drive.mount('/content/drive')

"""# База POLY

Обучение простой сети для прогнозирования временного ряда (только close) + визуализация.

Прогнозирование на 10 шагов вперёд прямым способом и визуализируйте результат.

Графики сравнения предсказания с оригинальным сигналом по всем 10 шагам предсказания (10 графиков на разных отдельных осях).
"""

# Commented out IPython magic to ensure Python compatibility.
#Загружаем библиотеки

import pandas as pd #Пандас
import matplotlib.pyplot as plt #Отрисовка графиков
from tensorflow.keras import utils #Для to_categorical
import numpy as np #Numpy
from tensorflow.keras.optimizers import Adam #Оптимизатор
from tensorflow.keras.models import Sequential, Model #Два варианта моделей
from tensorflow.keras.layers import concatenate, Input, Dense, Dropout, BatchNormalization, Flatten, Conv1D, LSTM #Стандартные слои
from sklearn.preprocessing import StandardScaler, MinMaxScaler #Нормировщики
from tensorflow.keras.preprocessing.sequence import TimeseriesGenerator # для генерации выборки временных рядов

# Рисовать графики сразу же
# %matplotlib inline

base_POLY_1d1 = pd.read_csv('/content/drive/MyDrive/T_R/POLY_1d_from_MOEX.txt', sep=',')
base_POLY_1d2 = pd.read_csv('/content/drive/MyDrive/T_R/POLY_1d_from_MOEX2.txt', sep=',')
dataPOLY_1d1 = base_POLY_1d1.iloc[:,4:]
dataPOLY_1d2 = base_POLY_1d2.iloc[:,4:]

dataPOLY_1d1.shape[0]

dataPOLY_1d1

# Объединяем базы из двух файлов
data = base_POLY_1d1.copy()                 # Создаем копию первой базы
data = pd.concat([dataPOLY_1d1,dataPOLY_1d2]) # Присоединяем к ней вторую базу
data = np.array(data)                   # Превращаем в numpy массив

print(len(data))      # Выводим размер базы

#Отображаем исходные от точки start и длинной step
start = 0            #С какой точки начинаем
step = 80 #data.shape[0] #Сколько точек отрисуем


#Заполняем текстовые названия каналов данных
chanelNames = ['OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOL']

#Рисуем все графики данных
#Четыре основных канала - open, max, min, close

plt.figure(figsize=(10, 10))
for i in range(4):
  #Отрисовываем часть данных
  #От начальной точки, до начальной точки + размер шага отрисовки
  plt.plot(data[start:start+step,i], 
          label=chanelNames[i])
plt.ylabel('Цена.руб')
plt.legend()
plt.show()

#Канал volume
plt.plot(data[start:start+step,+2], label="VOL")
plt.legend()
plt.show()

#Формируем параметры загрузки данных
xLen = 150  #Анализируем по 150 прошедшим точкам 
valLen = 3000                 #Используем 3000 записей для проверки
stepsForward = 1                 #шаг предсказания
trainLen = data.shape[0]-valLen #Размер тренировочной выборки
#Делим данные на тренировочную и тестовую выборки 
xTrain, xTest = data[:trainLen-stepsForward,2][..., None],  data[trainLen+xLen+2:-stepsForward,2][..., None]


#Делим данные на тренировочную и тестовую выборки 
xScaler = MinMaxScaler()
xScaler.fit(xTrain.reshape(-1,1))

xTrain = xScaler.transform(xTrain)
yTest = xScaler.transform(xTest)

#Для подготовки yTrain на 10 шагов вперед необходимо создать дополнительный датасет
yTrain = np.array([data[:trainLen, 4][i:i+stepsForward] for i in range(trainLen-stepsForward)])
yTest = np.array([data[trainLen+xLen+2:,4][i:i+stepsForward] for i in range(valLen-xLen-stepsForward-2)])
yScaler = MinMaxScaler()
yScaler.fit(yTrain)
yTrain = yScaler.transform(yTrain)
yTest = yScaler.transform(yTest)

#Создаем генератор для обучения
trainDataGen = TimeseriesGenerator(xTrain, yTrain,  #В качестве параметров наши выборки
                                   length=xLen, sampling_rate=1, #Для каждой точки
                                   batch_size=20) #Размер batch, который будем скармливать модели


testDataGen = TimeseriesGenerator(xTest, yTest, #В качестве параметров наши выборки
                                  length=xLen, sampling_rate=1, #Для каждой точки
                                  batch_size=20) #Размер batch, который будем скармливать модели

data.shape

yTrain[0]

xTrain[0]

print(trainDataGen[0][0].shape,
      trainDataGen[0][1].shape)

#Создаём нейронку
modelD = Sequential()
modelD.add(Dense(150,input_shape = (xLen,1), activation="linear" )) # 5 - количество каналов
modelD.add(Flatten())
modelD.add(Dense(yTrain.shape[1], activation="linear"))

#Компилируем
modelD.compile(loss="mse", optimizer=Adam(lr=1e-4))

#Запускаем обучение
history = modelD.fit_generator(
                    trainDataGen, 
                    epochs=20, 
                    verbose=1, 
                    validation_data = testDataGen 
                    )

#Выводим графики
plt.plot(history.history['loss'], 
         label='Средняя абсолютная ошибка на обучающем наборе')
plt.plot(history.history['val_loss'], 
         label='Средняя абсолютная ошибка на проверочном наборе')
plt.ylabel('Средняя ошибка')
plt.legend()
plt.show()

# Функция рассчитываем результаты прогнозирования сети
# В аргументы принимает сеть (currModel) и проверочную выборку
# Выдаёт результаты предсказания predVal
# И правильные ответы в исходной размерности yValUnscaled (какими они были до нормирования)
def getPred(currModel, xVal, yVal, yScaler):
  # Предсказываем ответ сети по проверочной выборке
  # И возвращаем исходны масштаб данных, до нормализации
  predVal = yScaler.inverse_transform(currModel.predict(xVal))
  yValUnscaled = yScaler.inverse_transform(yVal)
  
  return (predVal, yValUnscaled)

# Функция визуализирует графики, что предсказала сеть и какие были правильные ответы
# start - точка с которой начинаем отрисовку графика
# step - длина графика, которую отрисовываем
# channel - какой канал отрисовываем
def showPredict(start, step, channel, predVal, yValUnscaled):
  plt.plot(predVal[start:start+step, 0],
           label='Прогноз')
  plt.plot(yValUnscaled[start:start+step, channel], 
           label='Базовый ряд')
  plt.xlabel('Время')
  plt.ylabel('Значение Close')
  plt.legend()
  plt.show()
  
# Функция расёта корреляции дух одномерных векторов
def correlate(a, b):
  # Рассчитываем основные показатели
  ma = a.mean() # Среднее значение первого вектора
  mb = b.mean() # Среднее значение второго вектора
  mab = (a*b).mean() # Среднее значение произведения векторов
  sa = a.std() # Среднеквадратичное отклонение первого вектора
  sb = b.std() # Среднеквадратичное отклонение второго вектора
  
  #Рассчитываем корреляцию
  val = 1
  if ((sa>0) & (sb>0)):
    val = (mab-ma*mb)/(sa*sb)
  return val

# Функция рисуем корреляцию прогнозированного сигнала с правильным
# Смещая на различное количество шагов назад
# Для проверки появления эффекта автокорреляции
# channels - по каким каналам отображать корреляцию
# corrSteps - на какое количество шагов смещать сигнал назад для рассчёта корреляции
def showCorr(channels, corrSteps, predVal, yValUnscaled):
  # Проходим по всем каналам
  for ch in channels:
    corr = [] # Создаём пустой лист, в нём будут корреляции при смезении на i рагов обратно
    yLen = yValUnscaled.shape[0] # Запоминаем размер проверочной выборки

      # Постепенно увеличикаем шаг, насколько смещаем сигнал для проверки автокорреляции
    for i in range(corrSteps):
      # Получаем сигнал, смещённый на i шагов назад
      # predVal[i:, ch]
      # Сравниваем его с верными ответами, без смещения назад
      # yValUnscaled[:yLen-i,ch]
      # Рассчитываем их корреляцию и добавляем в лист
      corr.append(correlate(yValUnscaled[:yLen-i,ch], predVal[i:, 0]))

    own_corr = [] # Создаём пустой лист, в нём будут корреляции при смещении на i шагов обратно

      # Постепенно увеличиваем шаг, насколько смещаем сигнал для проверки автокорреляции
    for i in range(corrSteps):
      # Получаем сигнал, смещённый на i шагов назад
      # predVal[i:, ch]
      # Сравниваем его с верными ответами, без смещения назад
      # yValUnscaled[:yLen-i,ch]
      # Рассчитываем их корреляцию и добавляем в лист
      own_corr.append(correlate(yValUnscaled[:yLen-i,ch], yValUnscaled[i:, ch]))

    # Отображаем график коррелций для данного шага
    plt.plot(corr, label='Предсказание на ' + str(ch+1) + ' шаг')
    plt.plot(own_corr, label='Эталон')

  plt.xlabel('Время')
  plt.ylabel('Значение')
  plt.legend()
  plt.show()

#Создадим генератор проверочной выборки, из которой потом вытащим xVal, yVal для проверки
DataGen = TimeseriesGenerator(xTest, yTest,
                               length=xLen, sampling_rate=1,
                               batch_size=len(xTest)) #размер batch будет равен длине нашей выборки
xVal = []
yVal = []
for i in DataGen:
  xVal.append(i[0])
  yVal.append(i[1])

xVal = np.array(xVal)
yVal = np.array(yVal)

#Прогнозируем данные текущей сетью
currModel = modelD #Выбираем текущую модель
(predVal, yValUnscaled) = getPred(currModel, xVal[0], yVal[0], yScaler) #Прогнозируем данные

#Отображаем графики
for i in range(10):
    showPredict(0, 100, 0, predVal, yValUnscaled)

#Отображаем корреляцию
#Используем выходной канал - только close
#Проверяем корреляцию на глубину 60 шагов
showCorr([0], 60, predVal, yValUnscaled)

"""**ОДНОМЕРНАЯ СВЁРТКА**"""

modelC = Sequential()

modelC.add(Conv1D(200, 4, input_shape = (trainDataGen[0][0].shape[1:]), activation="linear"))
modelC.add(Flatten())
modelC.add(Dense(100, activation="linear"))
modelC.add(Dense(yTrain.shape[1], activation="linear"))

modelC.compile(loss="mse", optimizer=Adam(lr=1e-4))

history = modelC.fit_generator(trainDataGen,
                    epochs=20, 
                    verbose=1,
                    validation_data=testDataGen)
plt.plot(history.history['loss'], 
         label='Средняя абсолютная ошибка на обучающем наборе')
plt.plot(history.history['val_loss'], 
         label='Средняя абсолютная ошибка на проверочном наборе')
plt.ylabel('Средняя ошибка')
plt.legend()
plt.show()

trainDataGen[0][0].shape[1:]

#Прогнозируем данные текущей сетью
currModel = modelC
(predVal, yValUnscaled) = getPred(currModel, xVal[0], yVal[0], yScaler)

#Отображаем графики
showPredict(1000, 100, 0, predVal, yValUnscaled)

for i in range(1):
    showPredict(0, 150, i, predVal, yValUnscaled)

#Отображаем корреляцию
showCorr([0], 60, predVal, yValUnscaled)

"""**Сеть с предсказанием на один шаг и valLen = 900 из LSTM, Conv1D и/или Dense слоёв так, чтобы корреляция на старте была 99,9% и строго убывала.**

"""

#Формируем параметры загрузки данных
xLen = 90                    #Анализируем по 90 прошедшим точкам 
valLen = 900              #Используем 900 записей для проверки

trainLen = data.shape[0]-valLen  # Размер тренировочной выборки

#Делим данные на тренировочную и тестовую выборки 
xTrain, xTest = data[:trainLen], data[trainLen+xLen+2:]

#Масштабируем данные (отдельно для X и Y), чтобы их легче было скормить сетке
xScaler = MinMaxScaler()
xScaler.fit(xTrain)
xTrain = xScaler.transform(xTrain)
xTest = xScaler.transform(xTest)

#Делаем reshape,т.к. у нас только один столбец по одному значению
yTrain,yTest = np.reshape(data[:trainLen, 3],(-1,1)), np.reshape(data[trainLen+xLen+2:, 3], (-1, 1))
yScaler = MinMaxScaler()
yScaler.fit(yTrain)
yTrain = yScaler.transform(yTrain)
yTest = yScaler.transform(yTest)

#Создаем генератор для обучения
trainDataGen = TimeseriesGenerator(xTrain, yTrain, #В качестве параметров наши выборки
                                   length=xLen, sampling_rate=1,  #Для каждой точки (из промежутка длины xLen)  stride=1,
                                   batch_size=20)  #Размер batch, который будем скармливать модели

#Создаем аналогичный генератор для валидации при обучении
testDataGen = TimeseriesGenerator(xTest, yTest, #В качестве параметров наши выборки
                                  length=xLen, sampling_rate=1, #Для каждой точки (из промежутка длины xLen)  stride=1,
                                  batch_size=20)  #Размер batch, который будем скармливать модели

print(trainDataGen[0][0].shape,
      trainDataGen[0][1].shape)

# Функция рассчитываем результаты прогнозирования сети
# В аргументы принимает сеть (currModel) и проверочную выборку
# Выдаёт результаты предсказания predVal
# И правильные ответы в исходной размерности yValUnscaled (какими они были до нормирования)
def getPred(currModel, xVal, yVal, yScaler):
  # Предсказываем ответ сети по проверочной выборке
  # И возвращаем исходны масштаб данных, до нормализации
  predVal = yScaler.inverse_transform(currModel.predict(xVal))
  yValUnscaled = yScaler.inverse_transform(yVal)
  
  return (predVal, yValUnscaled)

# Функция визуализирует графики, что предсказала сеть и какие были правильные ответы
# start - точка с которой начинаем отрисовку графика
# step - длина графика, которую отрисовываем
# channel - какой канал отрисовываем
def showPredict(start, step, channel, predVal, yValUnscaled):
  plt.plot(predVal[start:start+step, 0],
           label='Прогноз')
  plt.plot(yValUnscaled[start:start+step, channel], 
           label='Базовый ряд')
  plt.xlabel('Время')
  plt.ylabel('Значение Close')
  plt.legend()
  plt.show()
  
# Функция расёта корреляции дух одномерных векторов
def correlate(a, b):
  # Рассчитываем основные показатели
  ma = a.mean() # Среднее значение первого вектора
  mb = b.mean() # Среднее значение второго вектора
  mab = (a*b).mean() # Среднее значение произведения векторов
  sa = a.std() # Среднеквадратичное отклонение первого вектора
  sb = b.std() # Среднеквадратичное отклонение второго вектора
  
  #Рассчитываем корреляцию
  val = 1
  if ((sa>0) & (sb>0)):
    val = (mab-ma*mb)/(sa*sb)
  return val

# Функция рисуем корреляцию прогнозированного сигнала с правильным
# Смещая на различное количество шагов назад
# Для проверки появления эффекта автокорреляции
# channels - по каким каналам отображать корреляцию
# corrSteps - на какое количество шагов смещать сигнал назад для рассчёта корреляции
def showCorr(channels, corrSteps, predVal, yValUnscaled):
  # Проходим по всем каналам
  for ch in channels:
    corr = [] # Создаём пустой лист, в нём будут корреляции при смезении на i рагов обратно
    yLen = yValUnscaled.shape[0] # Запоминаем размер проверочной выборки

      # Постепенно увеличикаем шаг, насколько смещаем сигнал для проверки автокорреляции
    for i in range(corrSteps):
      # Получаем сигнал, смещённый на i шагов назад
      # predVal[i:, ch]
      # Сравниваем его с верными ответами, без смещения назад
      # yValUnscaled[:yLen-i,ch]
      # Рассчитываем их корреляцию и добавляем в лист
      corr.append(correlate(yValUnscaled[:yLen-i,ch], predVal[i:, 0]))

    own_corr = [] # Создаём пустой лист, в нём будут корреляции при смещении на i шагов обратно

      # Постепенно увеличиваем шаг, насколько смещаем сигнал для проверки автокорреляции
    for i in range(corrSteps):
      # Получаем сигнал, смещённый на i шагов назад
      # predVal[i:, ch]
      # Сравниваем его с верными ответами, без смещения назад
      # yValUnscaled[:yLen-i,ch]
      # Рассчитываем их корреляцию и добавляем в лист
      own_corr.append(correlate(yValUnscaled[:yLen-i,ch], yValUnscaled[i:, ch]))

    # Отображаем график коррелций для данного шага
    plt.plot(corr, label='Предсказание на ' + str(ch+1) + ' шаг')
    plt.plot(own_corr, label='Эталон')

  plt.xlabel('Время')
  plt.ylabel('Значение')
  plt.legend()
  plt.show()

#Создадим генератор проверочной выборки, из которой потом вытащим xVal, yVal для проверки
DataGen = TimeseriesGenerator(xTest, yTest,
                               length=xLen, sampling_rate=1,
                               batch_size=len(xTest)) #размер batch будет равен длине нашей выборки
xVal = []
yVal = []
for i in DataGen:
  xVal.append(i[0])
  yVal.append(i[1])

xVal = np.array(xVal)
yVal = np.array(yVal)

yVal[0].shape

modelC = Sequential()

modelC.add(Conv1D(300, 5, input_shape = (xLen,5), activation="linear"))
modelC.add(Flatten())

modelC.add(Dense(300, activation="linear"))
modelC.add(Dense(1, activation="linear"))

modelC.compile(loss="mse", optimizer=Adam(lr=1e-4))

history = modelC.fit_generator(trainDataGen,
                    epochs=20, 
                    verbose=1,
                    validation_data=testDataGen)

plt.plot(history.history['loss'], 
         label='Средняя абсолютная ошибка на обучающем наборе')
plt.plot(history.history['val_loss'], 
         label='Средняя абсолютная ошибка на проверочном наборе')
plt.ylabel('Средняя ошибка')
plt.legend()
plt.show()

#Прогнозируем данные текущей сетью
currModel = modelC
(predVal, yValUnscaled) = getPred(currModel, xVal[0], yVal[0], yScaler)

#Отображаем графики
showPredict(100, 40, 0, predVal, yValUnscaled)

#Отображаем корреляцию
showCorr([0], 10, predVal, yValUnscaled)

"""**Несколько усовершенствований в предсказании временного ряда.
Добавляем к исходному сигналу расширенные данные:**

* попарные разности каналов
* модули попарных разностей каналов
* попарные произведения каналов
* обратное значение каналов x_new = 1/(x + 1e-3)
* первые производные каналов (x[n] - x[n-1])
* вторые производные каналов (x[n] - 2*x[n-1] + x[n-2])

Просмотр сети в прошлое, при формировании входного сигнала используем

* 100 точек с шагом назад по 1,

* 100 точек с шагом назад по 10 (или сами точки, или среднее по отрезку в 10 точек).

"""

# Commented out IPython magic to ensure Python compatibility.
#Загружаем библиотеки

import pandas as pd #Пандас
import matplotlib.pyplot as plt #Отрисовка графиков
from tensorflow.keras import utils #Для to_categorical
import numpy as np #Numpy
from tensorflow.keras.optimizers import Adam #Оптимизатор
from tensorflow.keras.models import Sequential, Model #Два варианты моделей
from tensorflow.keras.layers import concatenate, Input, Dense, Dropout, BatchNormalization, Flatten, Conv1D, LSTM #Стандартные слои
from sklearn.preprocessing import StandardScaler, MinMaxScaler #Нормировщики
from tensorflow.keras.preprocessing.sequence import TimeseriesGenerator # для генерации выборки временных рядов

# Рисовать графики сразу же
# %matplotlib inline

base_POLY_1d1 = pd.read_csv('/content/drive/MyDrive/T_R/POLY_1d_from_MOEX.txt', sep=',')
base_POLY_1d2 = pd.read_csv('/content/drive/MyDrive/T_R/POLY_1d_from_MOEX2.txt', sep=',')
dataPOLY_1d1 = base_POLY_1d1.iloc[:,4:]
dataPOLY_1d2 = base_POLY_1d2.iloc[:,4:]
data = pd.concat([dataPOLY_1d1,dataPOLY_1d2]) # Объединяем
data = data.reset_index(drop = True) #Обнуляем индесы
data #Выводим таблицу

col = data.columns #Получаем названия столбцов
print(col) #Выводим

#Задаем циклы для столбцов таким образом, чтобы происходил перебор всех возможных пар:
#Проходим по индексам массива с именами столбцов 'OPEN', 'MAX', 'MIN', 'CLOSE', 'VOLUME', 
#получая пары 'OPEN' и 'HIGH', 'OPEN' и 'LOW', 'OPEN' и 'CLOSE' ..., 'MAX' и 'MIN', 'MAX' и 'CLOSE' и т.д
for i in range(col.shape[0]):                                                   #Для всех пар
  for j in range(i + 1 , col.shape[0]):                                         #Считаем
    data[col[i] + '-' + col[j]] = data[col[i]] - data[col[j]]                   #Разности
    data['|' + col[i] + '-' + col[j] + '|'] = abs(data[col[i]] - data[col[j]])  #Модули разностей
    data[col[i] + '*' + col[j]] = data[col[i]] * data[col[j]]                   #Произведения

#Для каждого столбца 'OPEN', 'MAX', 'MIN', 'CLOSE', 'VOLUME' считаем:
for i in col:
  data['Обратный ' + i] = 1 / (data[i] + 1e-3) #обратные значения. 1e-3 в формуле нужно, чтобы случайно не разделить на 0
  data['Производная от ' + i] = np.nan #Создаем пустой столбец 
  data['Производная от ' + i][1:] = data[i][1:].reset_index(drop=True) - data[i][:-1].reset_index(drop=True) #При помощи срезов считаем первые производные .reset_index(drop=True) нужен для корректных подсчетов
  data['Вторая производная от ' + i] = np.nan #Создаем пустой столбец 
  data['Вторая производная от ' + i][2:] = data[i][2:].reset_index(drop=True) - 2 * data[i][1:-1].reset_index(drop=True) + data[i][:-2].reset_index(drop=True) #При помощи срезов считаем вторые производные

data #Смотрим что получилось

data = np.array(data.iloc[2:]) #Берем все столбцы с первых двух
data = np.array(data) #Переводим в numpy
columnsamount = data.shape[1] #При помощи этой переменной будем использовать одну и ту же архитетуру под разные матрицы

"""**Функция загрузки данных**"""

#Формируем параметры загрузки данных

xLen = 30  #Анализируем по 30 прошедшим точкам 
valLen = 3000   #Используем 3000 записей для проверки

trainLen = data.shape[0]-valLen # Размер тренировочной выборки

#Делим данные на тренировочную и тестовую выборки 
xTrain,xTest = data[:trainLen], data[trainLen+xLen+2:]

#Масштабируем данные (отдельно для X и Y), чтобы их легче было скормить сетке
xScaler = MinMaxScaler()
xScaler.fit(xTrain)
xTrain = xScaler.transform(xTrain)
xTest = xScaler.transform(xTest)

#Делаем reshape,т.к. у нас только один столбец по одному значению
yTrain,yTest = np.reshape(data[:trainLen,3],(-1,1)), np.reshape(data[trainLen+xLen+2:,3],(-1,1)) 
yScaler = MinMaxScaler()
yScaler.fit(yTrain)
yTrain = yScaler.transform(yTrain)
yTest = yScaler.transform(yTest)

#Создаем генератор для обучения
trainDataGen = TimeseriesGenerator(xTrain, yTrain,           #В качестве параметров наши выборки
                               length=xLen, stride=1, #Для каждой точки (из промежутка длины xLen)
                               batch_size=20)                #Размер batch, который будем скармливать модели

#Создаем аналогичный генератор для валидации при обучении
testDataGen = TimeseriesGenerator(xTest, yTest,
                               length=xLen, stride=1,
                               batch_size=20)

xTrain[0]

print(trainDataGen[0][0].shape,
      trainDataGen[0][1].shape)

"""## Визуализация результатов"""

# Функция рассчитываем результаты прогнозирования сети
# В аргументы принимает сеть (currModel) и проверочную выборку
# Выдаёт результаты предсказания predVal
# И правильные ответы в исходной размерности yValUnscaled (какими они были до нормирования)
def getPred(currModel, xVal, yVal, yScaler):
  # Предсказываем ответ сети по проверочной выборке
  # И возвращаем исходны масштаб данных, до нормализации
  predVal = yScaler.inverse_transform(currModel.predict(xVal))
  yValUnscaled = yScaler.inverse_transform(yVal)
  
  return (predVal, yValUnscaled)

# Функция визуализирует графики, что предсказала сеть и какие были правильные ответы
# start - точка с которой начинаем отрисовку графика
# step - длина графика, которую отрисовываем
# channel - какой канал отрисовываем
def showPredict(start, step, channel, predVal, yValUnscaled):
  plt.plot(predVal[start:start+step, 0],
           label='Прогноз')
  plt.plot(yValUnscaled[start:start+step, channel], 
           label='Базовый ряд')
  plt.xlabel('Время')
  plt.ylabel('Значение Close')
  plt.legend()
  plt.show()
  
# Функция расёта корреляции дух одномерных векторов
def correlate(a, b):
  # Рассчитываем основные показатели
  ma = a.mean() # Среднее значение первого вектора
  mb = b.mean() # Среднее значение второго вектора
  mab = (a*b).mean() # Среднее значение произведения векторов
  sa = a.std() # Среднеквадратичное отклонение первого вектора
  sb = b.std() # Среднеквадратичное отклонение второго вектора
  
  #Рассчитываем корреляцию
  val = 1
  if ((sa>0) & (sb>0)):
    val = (mab-ma*mb)/(sa*sb)
  return val

# Функция рисуем корреляцию прогнозированного сигнала с правильным
# Смещая на различное количество шагов назад
# Для проверки появления эффекта автокорреляции
# channels - по каким каналам отображать корреляцию
# corrSteps - на какое количество шагов смещать сигнал назад для рассчёта корреляции
def showCorr(channels, corrSteps, predVal, yValUnscaled):
  # Проходим по всем каналам
  for ch in channels:
    corr = [] # Создаём пустой лист, в нём будут корреляции при смезении на i рагов обратно
    yLen = yValUnscaled.shape[0] # Запоминаем размер проверочной выборки

      # Постепенно увеличикаем шаг, насколько смещаем сигнал для проверки автокорреляции
    for i in range(corrSteps):
      # Получаем сигнал, смещённый на i шагов назад
      # predVal[i:, ch]
      # Сравниваем его с верными ответами, без смещения назад
      # yValUnscaled[:yLen-i,ch]
      # Рассчитываем их корреляцию и добавляем в лист
      corr.append(correlate(yValUnscaled[:yLen-i,ch], predVal[i:, 0]))

    own_corr = [] # Создаём пустой лист, в нём будут корреляции при смещении на i шагов обратно

      # Постепенно увеличиваем шаг, насколько смещаем сигнал для проверки автокорреляции
    for i in range(corrSteps):
      # Получаем сигнал, смещённый на i шагов назад
      # predVal[i:, ch]
      # Сравниваем его с верными ответами, без смещения назад
      # yValUnscaled[:yLen-i,ch]
      # Рассчитываем их корреляцию и добавляем в лист
      own_corr.append(correlate(yValUnscaled[:yLen-i,ch], yValUnscaled[i:, ch]))

    # Отображаем график коррелций для данного шага
    plt.plot(corr, label='Предсказание на ' + str(ch+1) + ' шаг')
    plt.plot(own_corr, label='Эталон')

  plt.xlabel('Время')
  plt.ylabel('Значение')
  plt.legend()
  plt.show()

#Создадим генератор проверочной выборки, из которой потом вытащим xVal, yVal для проверки
DataGen = TimeseriesGenerator(xTest, yTest,
                               length=xLen, sampling_rate=1,
                               batch_size=len(xTest)) #размер batch будет равен длине нашей выборки
xVal = []
yVal = []
for i in DataGen:
  xVal.append(i[0])
  yVal.append(i[1])

xVal = np.array(xVal)
yVal = np.array(yVal)

"""## Полносвязная сеть"""

#Создаём нейронку
modelD = Sequential()
modelD.add(Dense(150,input_shape = (xLen,columnsamount), activation="linear" )) 
modelD.add(Flatten())
modelD.add(Dense(1, activation="linear"))

#Компилируем
modelD.compile(loss="mse", optimizer=Adam(lr=1e-4))

#Запускаем обучение
history = modelD.fit_generator(
                    trainDataGen, 
                    epochs=20, 
                    verbose=1, 
                    validation_data = testDataGen 
                    )

#Выводим графики
plt.plot(history.history['loss'], 
         label='Средняя абсолютная ошибка на обучающем наборе')
plt.plot(history.history['val_loss'], 
         label='Средняя абсолютная ошибка на проверочном наборе')
plt.ylabel('Средняя ошибка')
plt.legend()
plt.show()

#Прогнозируем данные текущей сетью
currModel = modelD #Выбираем текущую модель
(predVal, yValUnscaled) = getPred(currModel, xVal[0], yVal[0], yScaler) #Прогнозируем данные

#Отображаем графики
showPredict(0, 160, 0, predVal, yValUnscaled)

#Отображаем корреляцию
#Используем выходной канал - только open
#Проверяем корреляцию на глубину 60 шагов
showCorr([0], 60, predVal, yValUnscaled)

#Выводим графики
plt.plot(history.history['loss'][2:], 
         label='Средняя абсолютная ошибка на обучающем наборе')
plt.plot(history.history['val_loss'][2:], 
         label='Средняя абсолютная ошибка на проверочном наборе')
plt.ylabel('Средняя ошибка')
plt.legend()
plt.show()

"""## Одномерная свёртка"""

modelC = Sequential()

modelC.add(Conv1D(200, 5, input_shape = (xLen, columnsamount), activation="linear"))
modelC.add(Flatten())
modelC.add(Dense(100, activation="linear"))
modelC.add(Dense(1, activation="linear"))

modelC.compile(loss="mse", optimizer=Adam(lr=1e-4))

history = modelC.fit_generator(trainDataGen,
                    epochs=20, 
                    verbose=1,
                    validation_data=testDataGen)

plt.plot(history.history['loss'], 
         label='Средняя абсолютная ошибка на обучающем наборе')
plt.plot(history.history['val_loss'], 
         label='Средняя абсолютная ошибка на проверочном наборе')
plt.ylabel('Средняя ошибка')
plt.legend()
plt.show()

#Прогнозируем данные текущей сетью
currModel = modelC
(predVal, yValUnscaled) = getPred(currModel, xVal[0], yVal[0], yScaler)

#Отображаем графики
showPredict(1000, 100, 0, predVal, yValUnscaled)

#Отображаем корреляцию
showCorr([0], 10, predVal, yValUnscaled)

"""## Увеличенный "просмотр сети в прошлое" без наращивания данных"""

base_POLY_1d1 = pd.read_csv('/content/drive/MyDrive/T_R/POLY_1d_from_MOEX.txt', sep=',')
base_POLY_1d2 = pd.read_csv('/content/drive/MyDrive/T_R/POLY_1d_from_MOEX2.txt', sep=',')
dataPOLY_1d1 = base_POLY_1d1.iloc[:,4:]
dataPOLY_1d2 = base_POLY_1d2.iloc[:,4:]
data = pd.concat([dataPOLY_1d1,dataPOLY_1d2]) # Объединяем
data = data.reset_index(drop = True) #Обнуляем индесы
data #Выводим таблицу

data = np.array(data) #Переводим в numpy
columnsamount = data.shape[1] #При помощи этой переменной будем использовать одну и ту же архитетуру под разные матрицы

#Собственная функция для формирования обучающей и тестовой выборки для временных рядов 
#numofpoints - число точек, выбираемых с определенным шагом
#stepamongpoints - шаг, с которым выбираются точки 
#continuouslinelen - длина выборки, выбираемая "как есть"
#stride - шаг, с которым предсказываем

def ourTimeseriesGenerator(xTrain, yTrain, numofpoints = 100, stepamongpoints = 10, continuouslinelen = 100, stride = 1):
  x, y, = [], [] #Создаем списки для x и для y

  index = 0 #Начальный индекс задаем равный нулю 

  #считаем длину вектора, который мы захватим при раскусывании на numofpoints точек с шагом stepamongpoints
  periodlinelen = stepamongpoints * (numofpoints - 1) + 1 

  #считаем длину вектора, который мы захватим при раскусывании на numofpoints точек с шагом stepamongpoints и на участок с непрерывной линией
  line = periodlinelen + continuouslinelen

  while index + line + stride < xTrain.shape[0]: # Определеям, позволяет ли длина выборки раскусить данные 

    endperiodline = index + periodlinelen #Вычисляем индекс, где закончится раскусывание с шагом
    periodline = xTrain[index:endperiodline:stepamongpoints] #Раскусываем с шагом
    continuousline = xTrain[endperiodline: endperiodline + continuouslinelen] #Берем непрерывную линию

    x.append(np.concatenate([periodline, continuousline])) #Объединяем две линии и добавляем в x
    y.append(yTrain[endperiodline + continuouslinelen - 1 + stride]) #Элемент, следующий после выборки x через шаг stride отправляем в y
    index += 1 #Увеличиваем индекс на 1

  x = np.array(x) #Преобразуем в numpy
  y = np.array(y) #Преобразуем в numpy
  
  return x, y #Возвращаем x и y

##Формируем параметры загрузки данных

valLen = 3000 #Используем 3000 записей для проверки
numofpoints = 100
stepamongpoints = 10
continuouslinelen = 100

trainLen = data.shape[0] - valLen # Размер тренировочной выборки

#Делим данные на тренировочную и тестовую выборки 
xTrain, xTest = data[:trainLen], data[trainLen + stepamongpoints * (numofpoints - 1) + 2:]

#Масштабируем данные (отдельно для X и Y), чтобы их легче было скормить сетке
xScaler = MinMaxScaler()
xScaler.fit(xTrain)
xTrain = xScaler.transform(xTrain)
xTest = xScaler.transform(xTest)

#Делаем reshape,т.к. у нас только один столбец по одному значению
yTrain,yTest = np.reshape(data[:trainLen,3],(-1,1)), np.reshape(data[trainLen + stepamongpoints * (numofpoints - 1) + 2:,3],(-1,1)) 
yScaler = MinMaxScaler()
yScaler.fit(yTrain)
yTrain = yScaler.transform(yTrain)
yTest = yScaler.transform(yTest)

xTrainFinal, yTrainFinal = ourTimeseriesGenerator(xTrain, yTrain)
xTestFinal, yTestFinal = ourTimeseriesGenerator(xTest, yTest)

print(xTrainFinal.shape)
print(yTrainFinal.shape)
print(xTestFinal.shape)
print(yTestFinal.shape)

#Создаём нейронку
modelD = Sequential()
modelD.add(Dense(150,input_shape = (200, columnsamount), activation="linear" )) 
modelD.add(Flatten())
modelD.add(Dense(1, activation="linear"))

#Компилируем
modelD.compile(loss="mse", optimizer=Adam(lr=1e-4))

#Запускаем обучение
history = modelD.fit(xTrainFinal,
                     yTrainFinal, 
                    epochs=20, 
                    verbose=1, 
                    validation_data = (xTestFinal, yTestFinal) 
                    )

#Выводим графики
plt.plot(history.history['loss'], 
         label='Средняя абсолютная ошибка на обучающем наборе')
plt.plot(history.history['val_loss'], 
         label='Средняя абсолютная ошибка на проверочном наборе')
plt.ylabel('Средняя ошибка')
plt.legend()
plt.show()

#Прогнозируем данные текущей сетью
currModel = modelD #Выбираем текущую модель
(predVal, yValUnscaled) = getPred(currModel, xTestFinal, yTestFinal, yScaler) #Прогнозируем данные

#Отображаем графики
showPredict(0, 160, 0, predVal, yValUnscaled)

#Отображаем корреляцию
showCorr([0], 10, predVal, yValUnscaled)